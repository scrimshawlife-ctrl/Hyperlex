"""EXECUTE_V6_FRESH_QUALIFICATION_ONCE.

Cold-load hardened V6 package, score QUAL-002 once, settle disposition.
No retrain / recalibrate / ontology change / QUAL mutation / QUAL-001 inspect.
"""

from __future__ import annotations

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

PRIVATE_QUAL = Path(
    "/home/morpheus/hlx-private/classification-v6-qualification-surface-002-20261001"
)
PRIVATE_PKG = Path(
    "/home/morpheus/hlx-private/classification-v6-semantic-pipeline-harden-20261001"
)
PRIVATE_EXEC = Path(
    "/home/morpheus/hlx-private/classification-v6-qualification-execute-002-20261001"
)
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-QUALIFICATION-EXECUTE-002"
)
REPO_HARDEN = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-SEMANTIC-PIPELINE-HARDEN-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
MAX_LEN = 192
BATCH = 32

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


def sudo_read_bytes(path: Path) -> bytes:
    if os.access(path, os.R_OK):
        return path.read_bytes()
    return subprocess.run(
        ["sudo", "-n", "cat", str(path)], check=True, capture_output=True
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


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as h:
        for r in rows:
            h.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
    os.chmod(path, 0o600)


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


def load_json(path: Path) -> Any:
    return json.loads(sudo_read_text(path))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in sudo_read_text(path).splitlines() if l.strip()]


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
        per[lab] = {
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "support": int(g[:, j].sum()),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
    m["per_label"] = per
    return m


def eval_scores(rows, scores_by_axis, vocabs, thresholds, tech_idx, ai_idx):
    from hyperlexical.classification_v6_architecture_bakeoff import (
        hierarchy_metrics,
        multilabel_f1,
    )

    packed: dict[str, Any] = {"n": len(rows)}
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
    return heads, bundle.get("meta") or {}


def scores_from_heads(heads, X, device):
    import torch

    out = {}
    with torch.no_grad():
        xt = torch.tensor(X, device=device)
        for axis, model in heads.items():
            out[axis] = torch.sigmoid(model(xt)).cpu().numpy()
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
        "sample_f1": float(packed["system"]["sample_f1"]),
        "jaccard": float(packed["system"]["jaccard"]),
    }


def preflight() -> dict[str, Any]:
    from hyperlexical.classification_v6_qualification_execute_002 import (
        EXPECTED_ENCODER_STATE_HASH,
        EXPECTED_HEAD_BUNDLE_SHA256,
        EXPECTED_N_ROWS,
        EXPECTED_PACKAGE_SHA256,
        EXPECTED_SEAL_SHA256,
        QUALIFICATION_ID,
        exact_int_equals,
        execute_contract,
    )
    from hyperlexical.classification_v6_semantic_pipeline_harden import (
        PACKAGE_ID,
        QUALIFICATION_GATES,
        SELECTED_ENCODER_MODEL_ID,
        SELECTED_ENCODER_REVISION,
        hierarchy_constraints_payload,
        pipeline_candidate_contract,
        threshold_manifest_payload,
    )
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text

    issues: list[str] = []
    seal = load_json(PRIVATE_QUAL / "QUALIFICATION_SEAL.json")
    manifest = load_json(PRIVATE_QUAL / "QUALIFICATION_MANIFEST.json")
    disjoint = load_json(PRIVATE_QUAL / "DISJOINTNESS_WITNESS.json")
    package = load_json(PRIVATE_PKG / "PACKAGE.json")
    heads_path = PRIVATE_PKG / "heads" / "axis_nonlinear_heads.pt"
    rows_path = PRIVATE_QUAL / "QUALIFICATION_ROWS.jsonl"

    if seal.get("QUALIFICATION_ID") != QUALIFICATION_ID:
        issues.append("qual_id_mismatch")
    if seal.get("QUALIFICATION_STATE") != "SEALED_UNSCORED":
        issues.append(f"state={seal.get('QUALIFICATION_STATE')}")
    if seal.get("seal_sha256") != EXPECTED_SEAL_SHA256:
        issues.append("seal_sha_mismatch")
    if int(seal.get("n_rows") or 0) != EXPECTED_N_ROWS:
        issues.append(f"n_rows_seal={seal.get('n_rows')}")
    if int(seal.get("qualification_model_executions") or 0) != 0:
        issues.append("model_executions_nonzero")
    if seal.get("evaluation_spent") not in (None, "UNSPENT"):
        issues.append(f"evaluation_spent={seal.get('evaluation_spent')}")

    rows_sha = sudo_sha256(rows_path)
    if rows_sha != seal.get("rows_sha256"):
        issues.append("rows_sha_mismatch")
    n_lines = sum(1 for l in sudo_read_text(rows_path).splitlines() if l.strip())
    if n_lines != EXPECTED_N_ROWS:
        issues.append(f"n_rows_file={n_lines}")

    if (not exact_int_equals(disjoint.get("forbidden_overlap"), 0)) or not disjoint.get(
        "pass"
    ):
        issues.append("forbidden_overlap")

    if package.get("PACKAGE_SHA256") != EXPECTED_PACKAGE_SHA256:
        issues.append("package_sha_mismatch")
    if package.get("PACKAGE_ID") != PACKAGE_ID:
        issues.append("package_id_mismatch")

    head_sha = sudo_sha256(heads_path)
    if head_sha != EXPECTED_HEAD_BUNDLE_SHA256:
        issues.append("head_bundle_sha_mismatch")
    if package.get("heads", {}).get("head_bundle_sha") != EXPECTED_HEAD_BUNDLE_SHA256:
        issues.append("package_head_sha_mismatch")

    enc = package.get("encoder") or {}
    if enc.get("state_hash") != EXPECTED_ENCODER_STATE_HASH:
        issues.append("encoder_state_hash_mismatch")
    if not exact_int_equals(enc.get("trainable_parameters"), 0):
        issues.append("encoder_trainable_nonzero")
    if enc.get("model_id") != SELECTED_ENCODER_MODEL_ID:
        issues.append("encoder_model_id_mismatch")
    if enc.get("revision") != SELECTED_ENCODER_REVISION:
        issues.append("encoder_revision_mismatch")

    # Ontology / threshold / constraint hashes vs live contracts
    cand = pipeline_candidate_contract()
    th_live = threshold_manifest_payload()
    hier_live = hierarchy_constraints_payload()
    th_sha_live = sha256_text(canonical_json(th_live))
    hier_sha_live = sha256_text(canonical_json(hier_live))
    if package.get("threshold_manifest_sha") != th_sha_live:
        # package may store hash of thresholds sub-object; compare ordered thresholds
        pkg_th = (package.get("thresholds") or {}).get("thresholds_ordered")
        live_th = th_live.get("thresholds_ordered")
        if pkg_th != live_th:
            issues.append("threshold_manifest_mismatch")
    pkg_rules = (package.get("hierarchy_constraints") or {}).get("rules")
    if pkg_rules != hier_live.get("rules"):
        issues.append("hierarchy_constraint_mismatch")

    # Gates frozen
    gates_art = load_json(REPO_HARDEN / "qualification_gates.json")
    if gates_art.get("gates") != QUALIFICATION_GATES and not (
        gates_art.get("gates", {}).get("system_macro_f1_min")
        == QUALIFICATION_GATES["system_macro_f1_min"]
        and gates_art.get("gates", {}).get("hierarchy_violation_max")
        == QUALIFICATION_GATES["hierarchy_violation_max"]
    ):
        issues.append("gates_mismatch")

    ok = not issues
    return {
        "ok": ok,
        "issues": issues,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "seal_sha256": seal.get("seal_sha256"),
        "package_sha256": package.get("PACKAGE_SHA256"),
        "head_bundle_sha256": head_sha,
        "encoder_state_hash": enc.get("state_hash"),
        "encoder_model_id": enc.get("model_id"),
        "encoder_revision": enc.get("revision"),
        "encoder_trainable_parameters": enc.get("trainable_parameters"),
        "n_rows": n_lines,
        "forbidden_overlap": disjoint.get("forbidden_overlap"),
        "qualification_model_executions": seal.get("qualification_model_executions"),
        "qualification_state": seal.get("QUALIFICATION_STATE"),
        "threshold_manifest_sha_live": th_sha_live,
        "constraint_manifest_sha_live": hier_sha_live,
        "ontology_label_schema_hash": cand["ontology"]["label_schema_hash"],
        "contract": execute_contract(),
        "package": package,
        "seal": seal,
        "manifest": manifest,
    }


def error_decomposition(rows, packed, vocabs):
    import numpy as np

    counts = Counter()
    patterns = defaultdict(int)
    tech = vocabs["domain"].index("domain.technology")
    ai = vocabs["domain"].index("domain.technology.ai_discourse")
    for i, r in enumerate(rows):
        for axis, key_fp, key_fn in (
            ("domain", "DOMAIN_FP", "DOMAIN_FN"),
            ("function", "FUNCTION_FP", "FUNCTION_FN"),
            ("mediation", "MEDIATION_FP", "MEDIATION_FN"),
        ):
            g = np.asarray(packed["golds"][axis][i])
            p = np.asarray(packed["preds"][axis][i])
            fp = int(((g == 0) & (p == 1)).sum())
            fn = int(((g == 1) & (p == 0)).sum())
            counts[key_fp] += fp
            counts[key_fn] += fn
        # parent-child on raw
        raw_d = np.asarray(packed["preds_raw"]["domain"][i])
        if raw_d[ai] == 1 and raw_d[tech] == 0:
            counts["PARENT_CHILD_VIOLATION"] += 1
        g_all = (
            list(packed["golds"]["domain"][i])
            + list(packed["golds"]["function"][i])
            + list(packed["golds"]["mediation"][i])
        )
        p_all = (
            list(packed["preds"]["domain"][i])
            + list(packed["preds"]["function"][i])
            + list(packed["preds"]["mediation"][i])
        )
        g_sum = sum(g_all)
        p_sum = sum(p_all)
        inter = sum(1 for a, b in zip(g_all, p_all) if a == 1 and b == 1)
        if g_sum >= 2 and inter < g_sum and p_sum > 0:
            counts["CO_LABEL_OMISSION"] += 1
            patterns["co_label_omission_multi_gold"] += 1
        if p_sum > g_sum + 1:
            counts["OVERPREDICTION"] += 1
        if r.get("ontology_uncertainty") in {
            "ONTOLOGY_BOUNDARY_UNCLEAR",
            "INSUFFICIENT_CONTEXT",
            "ANNOTATOR_DISAGREEMENT",
        }:
            if p_sum > 0 and g_sum == 0:
                counts["ONTOLOGY_BOUNDARY_CASE"] += 1
    return {
        "counts": dict(counts),
        "patterns": dict(patterns),
        "taxonomy": [
            "DOMAIN_FP",
            "DOMAIN_FN",
            "FUNCTION_FP",
            "FUNCTION_FN",
            "MEDIATION_FP",
            "MEDIATION_FN",
            "PARENT_CHILD_VIOLATION",
            "CO_LABEL_OMISSION",
            "OVERPREDICTION",
            "ONTOLOGY_BOUNDARY_CASE",
        ],
    }


def surface_kind(text: str, source_family: str | None, mediation_gold: list[str]) -> str:
    low = (text or "").lower()
    sf = source_family or ""
    if "wiki_none" in sf or "mediawiki_wiki" in sf:
        return "prose"
    if mediation_gold or "internet" in low or "online" in low or "slang" in sf:
        return "internet-register"
    if len(text) < 80 and text.endswith("."):
        return "definition-like"
    if any(x in low for x in ("i ", "you ", "we ", "lol", "imo")):
        return "conversational"
    if text.count(".") <= 1 and len(text) < 160:
        return "declarative"
    return "prose"


def inner() -> int:
    import numpy as np
    import torch

    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
    from hyperlexical.classification_v6_data_foundation import utc_now_iso
    from hyperlexical.classification_v6_qualification_execute_002 import (
        EXPECTED_ENCODER_STATE_HASH,
        EXPECTED_PACKAGE_SHA256,
        EXPECTED_SEAL_SHA256,
        PHASE_RULE,
        QUALIFICATION_ID,
        REP_REFERENCE_SYSTEM_MACRO_F1,
        RESULT_ID,
        classify_qual_label,
        classify_retention,
        classify_source_slice,
        decide_disposition,
        evaluate_gates,
        execute_contract,
    )
    from hyperlexical.classification_v6_semantic_pipeline_harden import (
        BAKEOFF_THRESHOLDS,
        PACKAGE_ID,
        PIPELINE_CANDIDATE_ID,
        SELECTED_ENCODER_MODEL_ID,
        SELECTED_ENCODER_REVISION,
    )
    from hyperlexical.classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256

    PRIVATE_EXEC.mkdir(mode=0o700, parents=True, exist_ok=True)
    print("preflight", flush=True)
    pf = preflight()
    write_private(PRIVATE_EXEC / "PREFLIGHT.json", pf)
    write_repo(REPO_ART / "preflight.json", {k: v for k, v in pf.items() if k not in {"package", "seal", "manifest", "contract"}})
    if not pf["ok"]:
        disposition = decide_disposition(
            preflight_ok=False, execution_ok=False, gate_pass=False
        )
        summary = {
            "QUALIFICATION_DISPOSITION": disposition["QUALIFICATION_DISPOSITION"],
            "NEXT_ACTION": disposition["NEXT_ACTION"],
            "RELEASE_ELIGIBLE": False,
            "preflight_ok": False,
            "issues": pf["issues"],
            "qualification_model_executions": 0,
            "evaluation_spent": "UNSPENT",
        }
        write_private(PRIVATE_EXEC / "SUMMARY.json", summary)
        write_repo(REPO_ART / "SUMMARY.json", summary)
        write_repo(REPO_ART / "summary.json", summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 2

    # Mark execution start (one-shot)
    seal = dict(pf["seal"])
    seal["qualification_model_executions"] = 1
    write_private(PRIVATE_QUAL / "QUALIFICATION_SEAL.json", seal)

    vocabs = {
        "domain": list(AXIS_VOCABS["domain"]),
        "function": list(AXIS_VOCABS["function"]),
        "mediation": list(AXIS_VOCABS["mediation"]),
    }
    thresholds = dict(BAKEOFF_THRESHOLDS)
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")

    rows = load_jsonl(PRIVATE_QUAL / "QUALIFICATION_ROWS.jsonl")
    assert len(rows) == pf["n_rows"]
    texts = [str(r.get("text") or "") for r in rows]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"cold_load device={device}", flush=True)

    heads_path = PRIVATE_PKG / "heads" / "axis_nonlinear_heads.pt"
    heads, head_meta = load_head_bundle(heads_path, 768, vocabs, device)
    head_sha = sudo_sha256(heads_path)

    print("encode_qual_once", flush=True)
    X, enc_hash, n_train = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        texts,
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    if n_train != 0:
        disposition = decide_disposition(
            preflight_ok=True, execution_ok=False, gate_pass=False
        )
        summary = {
            "QUALIFICATION_DISPOSITION": "V6_QUALIFICATION_INVALID",
            "NEXT_ACTION": "REPAIR_V6_QUALIFICATION_EXECUTION",
            "reason": "encoder_trainable_parameters_nonzero",
            "encoder_trainable_parameters": n_train,
        }
        write_private(PRIVATE_EXEC / "SUMMARY.json", summary)
        print(json.dumps(summary, indent=2))
        return 2
    if enc_hash != EXPECTED_ENCODER_STATE_HASH:
        disposition = decide_disposition(
            preflight_ok=True, execution_ok=False, gate_pass=False
        )
        summary = {
            "QUALIFICATION_DISPOSITION": "V6_QUALIFICATION_INVALID",
            "NEXT_ACTION": "REPAIR_V6_QUALIFICATION_EXECUTION",
            "reason": "runtime_encoder_hash_mismatch",
            "expected": EXPECTED_ENCODER_STATE_HASH,
            "got": enc_hash,
        }
        write_private(PRIVATE_EXEC / "SUMMARY.json", summary)
        print(json.dumps(summary, indent=2))
        return 2

    print("score_heads_once", flush=True)
    scores = scores_from_heads(heads, X, device)
    packed = eval_scores(rows, scores, vocabs, thresholds, tech_idx, ai_idx)

    # Persist raw predictions
    pred_rows = []
    for i, r in enumerate(rows):
        adj = []
        raw_d = packed["preds_raw"]["domain"][i]
        final_d = packed["preds"]["domain"][i]
        if raw_d[ai_idx] == 1 and raw_d[tech_idx] == 0:
            adj.append(
                {
                    "rule": "ai_discourse_requires_technology",
                    "action": "force_parent_positive",
                    "child": "domain.technology.ai_discourse",
                    "parent": "domain.technology",
                }
            )
        pred_rows.append(
            {
                "identity": r["identity"],
                "raw_domain_scores": [float(x) for x in scores["domain"][i]],
                "raw_function_scores": [float(x) for x in scores["function"][i]],
                "raw_mediation_scores": [float(x) for x in scores["mediation"][i]],
                "raw_domain_labels": [
                    vocabs["domain"][j]
                    for j, v in enumerate(packed["preds_raw"]["domain"][i])
                    if v == 1
                ],
                "raw_function_labels": [
                    vocabs["function"][j]
                    for j, v in enumerate(packed["preds_raw"]["function"][i])
                    if v == 1
                ],
                "raw_mediation_labels": [
                    vocabs["mediation"][j]
                    for j, v in enumerate(packed["preds_raw"]["mediation"][i])
                    if v == 1
                ],
                "constraint_adjustments": adj,
                "final_domain_labels": [
                    vocabs["domain"][j]
                    for j, v in enumerate(packed["preds"]["domain"][i])
                    if v == 1
                ],
                "final_function_labels": [
                    vocabs["function"][j]
                    for j, v in enumerate(packed["preds"]["function"][i])
                    if v == 1
                ],
                "final_mediation_labels": [
                    vocabs["mediation"][j]
                    for j, v in enumerate(packed["preds"]["mediation"][i])
                    if v == 1
                ],
                "encoder_sha": enc_hash,
                "head_bundle_sha": head_sha,
                "threshold_manifest_sha": pf["threshold_manifest_sha_live"],
                "ontology_sha": pf["ontology_label_schema_hash"],
                "constraint_sha": pf["constraint_manifest_sha_live"],
                "package_sha": EXPECTED_PACKAGE_SHA256,
                "qual_seal_sha": EXPECTED_SEAL_SHA256,
            }
        )
    write_jsonl(PRIVATE_EXEC / "RAW_PREDICTIONS.jsonl", pred_rows)

    # Load harden DEV/REP per-label for comparison
    harden_metrics = load_json(PRIVATE_PKG / "METRICS.json")
    dev_per = {}
    rep_per = {}
    for axis in vocabs:
        for lab, row in (harden_metrics.get("DEV", {}).get(axis, {}).get("per_label") or {}).items():
            dev_per[lab] = row
        for lab, row in (harden_metrics.get("REP", {}).get(axis, {}).get("per_label") or {}).items():
            rep_per[lab] = row
    # also flattened per_label_rep
    for lab, row in (harden_metrics.get("per_label_rep") or {}).items():
        rep_per.setdefault(lab, row)

    system_macro = float(packed["system"]["macro_f1"])
    axis_macros = {
        "domain": float(packed["domain"]["macro_f1"]),
        "function": float(packed["function"]["macro_f1"]),
        "mediation": float(packed["mediation"]["macro_f1"]),
    }
    gate_eval = evaluate_gates(
        system_macro_f1=system_macro,
        hierarchy_violation=float(packed["post_constraint_hierarchy_violation"]),
        axis_macros=axis_macros,
    )
    retention = classify_retention(system_macro, rep_macro=REP_REFERENCE_SYSTEM_MACRO_F1)
    # per-axis retention
    rep_axis = {
        "domain": float(harden_metrics["REP"]["domain"]["macro_f1"]),
        "function": float(harden_metrics["REP"]["function"]["macro_f1"]),
        "mediation": float(harden_metrics["REP"]["mediation"]["macro_f1"]),
    }
    retention["DOMAIN_retention"] = axis_macros["domain"] / max(1e-12, rep_axis["domain"])
    retention["FUNCTION_retention"] = axis_macros["function"] / max(
        1e-12, rep_axis["function"]
    )
    retention["MEDIATION_retention"] = axis_macros["mediation"] / max(
        1e-12, rep_axis["mediation"]
    )
    retention["per_axis_drop"] = {
        a: rep_axis[a] - axis_macros[a] for a in axis_macros
    }

    per_label = {}
    for axis, vocab in vocabs.items():
        for lab in vocab:
            q = packed[axis]["per_label"][lab]
            d = dev_per.get(lab) or {}
            rp = rep_per.get(lab) or {}
            cls = classify_qual_label(
                qual_f1=float(q["f1"]),
                support=int(q["support"]),
                rep_f1=float(rp["f1"]) if rp.get("f1") is not None else None,
            )
            per_label[lab] = {
                "axis": axis,
                "QUAL_support": int(q["support"]),
                "precision": float(q["precision"]),
                "recall": float(q["recall"]),
                "QUAL_f1": float(q["f1"]),
                "DEV_f1": float(d["f1"]) if d.get("f1") is not None else None,
                "REP_f1": float(rp["f1"]) if rp.get("f1") is not None else None,
                "class": cls,
            }

    # Cardinality / composition slices (by GOLD cardinality)
    def n_lab(r):
        return (
            len(r.get("domain_labels") or [])
            + len(r.get("function_labels") or [])
            + len(r.get("mediation_labels") or [])
        )

    card_masks = {
        "single_label": [n_lab(r) == 1 for r in rows],
        "two_label": [n_lab(r) == 2 for r in rows],
        "three_plus_label": [n_lab(r) >= 3 for r in rows],
        "domain_only": [
            bool(r.get("domain_labels"))
            and not r.get("function_labels")
            and not r.get("mediation_labels")
            for r in rows
        ],
        "function_only": [
            bool(r.get("function_labels"))
            and not r.get("domain_labels")
            and not r.get("mediation_labels")
            for r in rows
        ],
        "domain+function": [
            bool(r.get("domain_labels")) and bool(r.get("function_labels")) for r in rows
        ],
        "mediation_positive": [bool(r.get("mediation_labels")) for r in rows],
        "zero_label_gold": [n_lab(r) == 0 for r in rows],
    }
    cardinality_slices = {
        k: slice_eval(rows, scores, vocabs, thresholds, tech_idx, ai_idx, m)
        for k, m in card_masks.items()
    }

    # Source slices
    families = sorted({r.get("source_family") or "UNKNOWN" for r in rows})
    source_slices = {}
    fam_macros = {}
    for fam in families:
        mask = [(r.get("source_family") or "UNKNOWN") == fam for r in rows]
        det = slice_eval(rows, scores, vocabs, thresholds, tech_idx, ai_idx, mask)
        source_slices[fam] = det
        if det["n"] >= 8 and det["system_macro_f1"] is not None:
            fam_macros[fam] = float(det["system_macro_f1"])
    source_class = classify_source_slice(fam_macros, system_macro=system_macro)

    # Length / surface slices
    lenses = [len(r.get("text") or "") for r in rows]
    kinds = [
        surface_kind(
            r.get("text") or "",
            r.get("source_family"),
            r.get("mediation_labels") or [],
        )
        for r in rows
    ]
    length_slices = {
        "short": slice_eval(
            rows, scores, vocabs, thresholds, tech_idx, ai_idx, [n < 60 for n in lenses]
        ),
        "medium": slice_eval(
            rows,
            scores,
            vocabs,
            thresholds,
            tech_idx,
            ai_idx,
            [60 <= n < 200 for n in lenses],
        ),
        "long": slice_eval(
            rows, scores, vocabs, thresholds, tech_idx, ai_idx, [n >= 200 for n in lenses]
        ),
    }
    surface_slices = {
        kind: slice_eval(
            rows, scores, vocabs, thresholds, tech_idx, ai_idx, [k == kind for k in kinds]
        )
        for kind in sorted(set(kinds))
    }

    # Hierarchy / constraint contribution
    # degraded: cases where constraint flipped a correct tech=0 when ai gold absent?
    degraded = 0
    for i in range(len(rows)):
        raw = packed["preds_raw"]["domain"][i]
        final = packed["preds"]["domain"][i]
        gold = packed["golds"]["domain"][i]
        if raw[ai_idx] == 1 and raw[tech_idx] == 0 and final[tech_idx] == 1:
            # corrected; if gold tech is 0 and gold ai is 0, forcing parent adds FP
            if gold[tech_idx] == 0 and gold[ai_idx] == 0:
                degraded += 1

    hierarchy_analysis = {
        "raw_hierarchy_violation_rate": float(packed["raw_hierarchy_violation"] or 0.0),
        "post_constraint_hierarchy_violation_rate": float(
            packed["post_constraint_hierarchy_violation"]
        ),
        "predictions_corrected_by_constraints": int(packed["hierarchy_corrected"]),
        "predictions_degraded_by_constraints": degraded,
    }

    errors = error_decomposition(rows, packed, vocabs)

    # Baseline comparison (historical REP references only — not re-scored on QUAL)
    baselines = {
        "ModernBERT_zero_shot_REP_historical": 0.162,
        "MPNet_zero_shot_REP_historical": 0.206,
        "BGE_zero_shot_REP_historical": 0.243,
        "hardened_REP": REP_REFERENCE_SYSTEM_MACRO_F1,
        "QUAL_system_macro_f1": system_macro,
        "note": "Zero-shot baselines are historical REP references; not re-scored on QUAL.",
    }

    disposition = decide_disposition(
        preflight_ok=True, execution_ok=True, gate_pass=bool(gate_eval["pass"])
    )

    # EVALUATION_SPENT transition (always after valid one-shot)
    spent_seal = dict(seal)
    spent_seal["QUALIFICATION_STATE"] = "EVALUATION_SPENT"
    spent_seal["evaluation_spent"] = "EVALUATION_SPENT"
    spent_seal["qualification_model_executions"] = 1
    spent_seal["qualification_disposition"] = disposition["QUALIFICATION_DISPOSITION"]
    spent_seal["spent_at"] = utc_now_iso()
    spent_seal["seal_sha256_pre_spend"] = EXPECTED_SEAL_SHA256
    write_private(PRIVATE_QUAL / "QUALIFICATION_SEAL.json", spent_seal)
    # identity bar list
    identities = sorted(r["identity"] for r in rows)
    write_private(
        PRIVATE_QUAL / "EVALUATION_SPENT_IDENTITIES.json",
        {
            "QUALIFICATION_ID": QUALIFICATION_ID,
            "n": len(identities),
            "evaluation_spent": "EVALUATION_SPENT",
            "barred_from": [
                "TRAIN",
                "DEV",
                "REP",
                "calibration",
                "threshold_tuning",
                "model_selection",
                "representation_learning",
                "index_construction",
            ],
            "identity_sha256": sha256_text(canonical_json(identities)),
        },
    )

    primary = {
        "system_macro_f1": system_macro,
        "sample_f1": float(packed["system"]["sample_f1"]),
        "jaccard": float(packed["system"]["jaccard"]),
        "DOMAIN_macro_f1": axis_macros["domain"],
        "DOMAIN_micro_f1": float(packed["domain"]["micro_f1"]),
        "FUNCTION_macro_f1": axis_macros["function"],
        "FUNCTION_micro_f1": float(packed["function"]["micro_f1"]),
        "MEDIATION_macro_f1": axis_macros["mediation"],
        "MEDIATION_micro_f1": float(packed["mediation"]["micro_f1"]),
        "hierarchy_violation_rate": float(packed["post_constraint_hierarchy_violation"]),
        "raw_hierarchy_violation_rate": float(packed["raw_hierarchy_violation"] or 0.0),
    }

    result = {
        "RESULT_ID": RESULT_ID,
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": "HLX-CLASSIFICATION-V6-QUALIFICATION-EXECUTE-002",
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "QUAL_seal_sha256": EXPECTED_SEAL_SHA256,
        "package_sha256": EXPECTED_PACKAGE_SHA256,
        "PACKAGE_ID": PACKAGE_ID,
        "PIPELINE_CANDIDATE_ID": PIPELINE_CANDIDATE_ID,
        "encoder_sha": enc_hash,
        "encoder_model_id": SELECTED_ENCODER_MODEL_ID,
        "encoder_revision": SELECTED_ENCODER_REVISION,
        "encoder_trainable_parameters": 0,
        "head_bundle_sha": head_sha,
        "threshold_manifest_sha": pf["threshold_manifest_sha_live"],
        "ontology_sha": pf["ontology_label_schema_hash"],
        "constraint_sha": pf["constraint_manifest_sha_live"],
        "qualification_model_executions": 1,
        "n_rows": len(rows),
        "primary_metrics": primary,
        "axis_metrics": {
            "domain": {
                k: packed["domain"][k]
                for k in ("macro_f1", "micro_f1", "sample_f1", "jaccard")
            },
            "function": {
                k: packed["function"][k]
                for k in ("macro_f1", "micro_f1", "sample_f1", "jaccard")
            },
            "mediation": {
                k: packed["mediation"][k]
                for k in ("macro_f1", "micro_f1", "sample_f1", "jaccard")
            },
        },
        "per_label": per_label,
        "REP_retention": retention,
        "hierarchy_analysis": hierarchy_analysis,
        "cardinality_slices": cardinality_slices,
        "source_slices": {
            "families": source_slices,
            "classification": source_class,
            "families_with_n_ge_8": fam_macros,
        },
        "length_slices": length_slices,
        "surface_slices": surface_slices,
        "constraint_contribution": hierarchy_analysis,
        "error_decomposition": errors,
        "gate_results": gate_eval,
        "baselines_historical_REP": baselines,
        "QUALIFICATION_DISPOSITION": disposition["QUALIFICATION_DISPOSITION"],
        "RELEASE_ELIGIBLE": disposition["RELEASE_ELIGIBLE"],
        "HUB_PUBLISH_AUTHORIZED": False,
        "V6_REPRESENTATION_CANDIDATE_STATUS": disposition[
            "V6_REPRESENTATION_CANDIDATE_STATUS"
        ],
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "V5_POINTERS_MUTATED": False,
        "evaluation_spent": "EVALUATION_SPENT",
        "NEXT_ACTION": disposition["NEXT_ACTION"],
        "code_revision": code_revision(),
        "settled_at": utc_now_iso(),
        "head_meta": head_meta,
    }
    result["V6_QUALIFICATION_002_RESULT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in result.items()
                if k != "V6_QUALIFICATION_002_RESULT_SHA256"
            }
        )
    )

    write_private(PRIVATE_EXEC / "RESULT.json", result)
    write_private(PRIVATE_EXEC / "PRIMARY_METRICS.json", primary)
    write_private(PRIVATE_EXEC / "PER_LABEL.json", per_label)
    write_private(PRIVATE_EXEC / "GATES.json", gate_eval)
    write_private(PRIVATE_EXEC / "RETENTION.json", retention)
    write_private(PRIVATE_EXEC / "HIERARCHY.json", hierarchy_analysis)
    write_private(PRIVATE_EXEC / "ERROR_DECOMPOSITION.json", errors)
    write_private(PRIVATE_EXEC / "CARDINALITY_SLICES.json", cardinality_slices)
    write_private(PRIVATE_EXEC / "SOURCE_SLICES.json", result["source_slices"])
    write_private(
        PRIVATE_EXEC / "LENGTH_SURFACE_SLICES.json",
        {"length": length_slices, "surface": surface_slices},
    )

    # public artifacts (no row texts / raw prediction scores)
    public = {
        k: v
        for k, v in result.items()
        if k
        not in {
            "head_meta",
        }
    }
    # trim source family detail in public to top macros only
    public["source_slices"] = {
        "classification": source_class,
        "families_with_n_ge_8": fam_macros,
        "n_families": len(source_slices),
    }
    write_repo(REPO_ART / "result.json", public)
    write_repo(REPO_ART / "RESULT.json", public)
    write_repo(REPO_ART / "primary_metrics.json", primary)
    write_repo(REPO_ART / "per_label.json", per_label)
    write_repo(REPO_ART / "gates.json", gate_eval)
    write_repo(REPO_ART / "retention.json", retention)
    write_repo(REPO_ART / "hierarchy.json", hierarchy_analysis)
    write_repo(REPO_ART / "error_decomposition.json", errors)
    write_repo(REPO_ART / "cardinality_slices.json", cardinality_slices)
    write_repo(
        REPO_ART / "source_slices.json",
        {"classification": source_class, "families_with_n_ge_8": fam_macros},
    )
    write_repo(
        REPO_ART / "length_surface_slices.json",
        {"length": length_slices, "surface": surface_slices},
    )
    write_repo(REPO_ART / "baselines_historical_REP.json", baselines)
    write_repo(REPO_ART / "preflight.json", {k: pf[k] for k in pf if k not in {"package", "seal", "manifest", "contract"}})
    write_repo(REPO_ART / "execute_contract.json", execute_contract())

    pointer = {
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "STAGE_A_BEST_MUTATED": False,
        "V5_POINTERS_MUTATED": False,
        "V6_REPRESENTATION_CANDIDATE": EXPECTED_PACKAGE_SHA256,
        "V6_REPRESENTATION_CANDIDATE_STATUS": disposition[
            "V6_REPRESENTATION_CANDIDATE_STATUS"
        ],
        "HUB_PUBLISH_AUTHORIZED": False,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "QUALIFICATION_DISPOSITION": disposition["QUALIFICATION_DISPOSITION"],
        "evaluation_spent": "EVALUATION_SPENT",
    }
    write_private(PRIVATE_EXEC / "POINTER.json", pointer)
    write_repo(REPO_ART / "pointer.json", pointer)
    write_repo(REPO_ART / "POINTER.json", pointer)

    summary = {
        "QUALIFICATION_DISPOSITION": disposition["QUALIFICATION_DISPOSITION"],
        "NEXT_ACTION": disposition["NEXT_ACTION"],
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "RELEASE_ELIGIBLE": disposition["RELEASE_ELIGIBLE"],
        "HUB_PUBLISH_AUTHORIZED": False,
        "V6_REPRESENTATION_CANDIDATE_STATUS": disposition[
            "V6_REPRESENTATION_CANDIDATE_STATUS"
        ],
        "system_macro_f1": system_macro,
        "DOMAIN_macro_f1": axis_macros["domain"],
        "FUNCTION_macro_f1": axis_macros["function"],
        "MEDIATION_macro_f1": axis_macros["mediation"],
        "sample_f1": primary["sample_f1"],
        "jaccard": primary["jaccard"],
        "hierarchy_violation": primary["hierarchy_violation_rate"],
        "retention_band": retention["band"],
        "retention_ratio": retention["retention_ratio"],
        "gate_pass": gate_eval["pass"],
        "n_rows": len(rows),
        "qualification_model_executions": 1,
        "evaluation_spent": "EVALUATION_SPENT",
        "RESULT_SHA256": result["V6_QUALIFICATION_002_RESULT_SHA256"],
        "MODEL_WIDE_BEST_MUTATED": False,
        "preflight_ok": True,
        "encoder_trainable_parameters": 0,
    }
    write_private(PRIVATE_EXEC / "SUMMARY.json", summary)
    write_private(PRIVATE_EXEC / "RECEIPT.json", result)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(REPO_ART / "summary.json", summary)
    write_repo(REPO_ART / "receipt.json", public)
    write_repo(REPO_ART / "RECEIPT.json", public)
    write_repo(
        SPEC / "classification-v6-qualification-execute-002-receipt-20261001.json",
        public,
    )

    md = f"""# EXECUTE_V6_FRESH_QUALIFICATION_ONCE

```text
QUALIFICATION_DISPOSITION = {disposition['QUALIFICATION_DISPOSITION']}
QUALIFICATION_ID = {QUALIFICATION_ID}
RELEASE_ELIGIBLE = {disposition['RELEASE_ELIGIBLE']}
system_macro_F1 = {system_macro:.4f}
hierarchy_violation = {primary['hierarchy_violation_rate']:.4f}
retention = {retention['band']} ({retention['retention_ratio']:.4f})
evaluation_spent = EVALUATION_SPENT
NEXT_ACTION = {disposition['NEXT_ACTION']}
RESULT = {result['V6_QUALIFICATION_002_RESULT_SHA256']}
```

Cold-loaded `{PACKAGE_ID}` (`{EXPECTED_PACKAGE_SHA256[:12]}…`).
Encoder trainable parameters = 0. One-shot execution on {len(rows)} QUAL-002 rows.
MODEL_WIDE_BEST / V5 pointers unchanged. HUB_PUBLISH_AUTHORIZED = false.
"""
    write_repo(SPEC / "classification-v6-qualification-execute-002-20261001.md", md)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if disposition["QUALIFICATION_DISPOSITION"] != "V6_QUALIFICATION_INVALID" else 2


def main() -> int:
    if os.environ.get("HLX_V6_QUAL_EXEC_INNER") == "1":
        return inner()
    PRIVATE_EXEC.mkdir(mode=0o700, parents=True, exist_ok=True)
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
        "HLX_V6_QUAL_EXEC_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v6_qualification_execute_002.py"),
    ]
    log = PRIVATE_EXEC / "qual_exec_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, check=False, stdout=handle, stderr=subprocess.STDOUT)
    try:
        print(log.read_text(encoding="utf-8")[-50000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
