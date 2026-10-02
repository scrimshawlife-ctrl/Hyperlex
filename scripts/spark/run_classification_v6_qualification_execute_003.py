"""EXECUTE_V6_QUALIFICATION_003_ONCE.

Cold-load hardened operating package (encoder → ANY_LABEL gate → heads →
hierarchy), score QUAL-003 once, settle disposition. No retrain / recalibrate /
threshold change / QUAL mutation / QUAL-002 inspect / pointer moves.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE_QUAL = Path(
    "/home/morpheus/hlx-private/classification-v6-qualification-surface-003-20261001"
)
PRIVATE_PKG = Path(
    "/home/morpheus/hlx-private/classification-v6-operating-pipeline-harden-20261001"
)
PRIVATE_EXEC = Path(
    "/home/morpheus/hlx-private/classification-v6-qualification-execute-003-20261001"
)
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-QUALIFICATION-EXECUTE-003"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
MAX_LEN = 192
BATCH = 32

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    d = hashlib.sha256()
    with path.open("rb") as h:
        for chunk in iter(lambda: h.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


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


def multi_hot(labels: list[str] | None, vocab: list[str]) -> list[int]:
    idx = {v: i for i, v in enumerate(vocab)}
    vec = [0] * len(vocab)
    for lab in labels or []:
        if lab in idx:
            vec[idx[lab]] = 1
    return vec


def mean_pool(last_hidden, attention_mask):
    mask = attention_mask.unsqueeze(-1).float()
    return (last_hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-6)


def n_lab(r: dict) -> int:
    return (
        len(r.get("domain_labels") or [])
        + len(r.get("function_labels") or [])
        + len(r.get("mediation_labels") or [])
    )


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
    return float(sum(f1_binary(g[:, j], p[:, j]) for j in range(g.shape[1])) / g.shape[1])


def pack_axis(gold, pred, vocab):
    import numpy as np
    from hyperlexical.classification_v6_architecture_bakeoff import multilabel_f1

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


def run_gated_once(rows, X, heads, gate, gate_th, vocabs, thresholds, tech_idx, ai_idx, device):
    """Operating forward: heads → ANY_LABEL gate zeroing → hierarchy."""
    import numpy as np
    from hyperlexical.classification_v6_architecture_bakeoff import multilabel_f1

    scores = scores_from_heads(heads, X, device)
    gsc = gate_scores(gate, X, device)
    reject = gsc < float(gate_th)

    preds_pre_gate = {}
    preds_gated = {}
    for a in vocabs:
        th = np.asarray(thresholds[a])
        raw = (np.asarray(scores[a]) >= th).astype(np.int32)
        preds_pre_gate[a] = raw
        q = raw.copy()
        q[reject] = 0
        preds_gated[a] = q

    # Hierarchy on gated domain
    d = preds_gated["domain"].copy()
    raw_viol = 0
    hier_corr = 0
    for i in range(d.shape[0]):
        if d[i, ai_idx] == 1 and d[i, tech_idx] == 0:
            raw_viol += 1
            d[i, tech_idx] = 1
            hier_corr += 1
    preds_final = {
        "domain": d,
        "function": preds_gated["function"],
        "mediation": preds_gated["mediation"],
    }
    post_viol = 0
    for i in range(d.shape[0]):
        if d[i, ai_idx] == 1 and d[i, tech_idx] == 0:
            post_viol += 1

    golds = {
        a: np.asarray(
            [multi_hot(r.get(f"{a}_labels"), vocabs[a]) for r in rows], dtype=np.int32
        )
        for a in vocabs
    }
    packed_axes = {a: pack_axis(golds[a], preds_final[a], vocabs[a]) for a in vocabs}
    axis_macros = {a: float(packed_axes[a]["macro_f1"]) for a in vocabs}
    # Operating system macro = mean of axis macros (matches REP_V2 witness 0.370).
    system_macro = float(sum(axis_macros.values()) / len(axis_macros))

    g_sys = [
        list(golds["domain"][i])
        + list(golds["function"][i])
        + list(golds["mediation"][i])
        for i in range(len(rows))
    ]
    p_sys = [
        list(preds_final["domain"][i])
        + list(preds_final["function"][i])
        + list(preds_final["mediation"][i])
        for i in range(len(rows))
    ]
    sys_ml = multilabel_f1(g_sys, p_sys)

    zero_idx = [i for i, r in enumerate(rows) if n_lab(r) == 0]
    pos_idx = [i for i, r in enumerate(rows) if n_lab(r) > 0]
    zero_fp = zero_exact = 0
    pred_counts = []
    for i in zero_idx:
        npred = int(
            preds_final["domain"][i].sum()
            + preds_final["function"][i].sum()
            + preds_final["mediation"][i].sum()
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
            preds_final["domain"][i].sum()
            + preds_final["function"][i].sum()
            + preds_final["mediation"][i].sum()
        )
        if npred == 0:
            false_reject += 1
    n_pos = max(1, len(pos_idx))

    def slice_macro(idx):
        if not idx:
            return None
        return float(
            sum(macro_f1(golds[a][idx], preds_final[a][idx]) for a in vocabs)
            / len(vocabs)
        )

    return {
        "n": len(rows),
        "system_macro_f1": system_macro,
        "sample_f1": float(sys_ml["sample_f1"]),
        "jaccard": float(sys_ml["jaccard"]),
        "axis_macros": axis_macros,
        "packed_axes": packed_axes,
        "zero_label_n": len(zero_idx),
        "positive_n": len(pos_idx),
        "zero_label_false_positive_rate": zero_fp / n_zero,
        "zero_label_exact_rejection": zero_exact / n_zero,
        "mean_predicted_labels_on_zero_gold": float(sum(pred_counts) / n_zero),
        "false_reject_positive_rate": false_reject / n_pos,
        "positive_only_system_macro_f1": slice_macro(pos_idx) or 0.0,
        "single_label_system_macro_f1": slice_macro(
            [i for i, r in enumerate(rows) if n_lab(r) == 1]
        ),
        "multi_label_system_macro_f1": slice_macro(
            [i for i, r in enumerate(rows) if n_lab(r) >= 2]
        ),
        "raw_hierarchy_violation_rate": raw_viol / max(1, len(rows)),
        "post_constraint_hierarchy_violation_rate": post_viol / max(1, len(rows)),
        "hierarchy_corrections": hier_corr,
        "n_gated_zero": int(reject.sum()),
        "gate_scores": gsc.tolist(),
        "preds": {a: preds_final[a].tolist() for a in vocabs},
        "preds_pre_gate": {a: preds_pre_gate[a].tolist() for a in vocabs},
        "preds_gated_pre_hier": {a: preds_gated[a].tolist() for a in vocabs},
        "golds": {a: golds[a].tolist() for a in vocabs},
        "scores": {a: scores[a].tolist() for a in vocabs},
    }


def preflight() -> dict[str, Any]:
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v6_operating_pipeline_harden import (
        OPERATING_QUALIFICATION_GATES,
        PACKAGE_ID,
        WITNESS_GATE_BUNDLE_SHA256,
        WITNESS_GATE_THRESHOLD,
    )
    from hyperlexical.classification_v6_qualification_execute_002 import (
        EXPECTED_ENCODER_STATE_HASH,
        EXPECTED_HEAD_BUNDLE_SHA256,
    )
    from hyperlexical.classification_v6_qualification_execute_003 import (
        EXPECTED_N_ROWS,
        EXPECTED_PACKAGE_SHA256,
        EXPECTED_SEAL_SHA256,
        QUALIFICATION_ID,
        exact_int_equals,
        execute_contract,
    )
    from hyperlexical.classification_v6_semantic_pipeline_harden import (
        SELECTED_ENCODER_MODEL_ID,
        SELECTED_ENCODER_REVISION,
        hierarchy_constraints_payload,
        threshold_manifest_payload,
    )

    issues: list[str] = []
    seal = load_json(PRIVATE_QUAL / "QUALIFICATION_SEAL.json")
    disjoint = load_json(PRIVATE_QUAL / "DISJOINTNESS_WITNESS.json")
    package = load_json(PRIVATE_PKG / "PACKAGE.json")
    heads_path = PRIVATE_PKG / "heads" / "axis_nonlinear_heads.pt"
    gate_path = PRIVATE_PKG / "heads" / "any_evidence_gate.pt"
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
    if seal.get("evaluation_spent") not in (None, "UNSPENT", False):
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
    if package.get("heads", {}).get("bundle_sha256") != EXPECTED_HEAD_BUNDLE_SHA256:
        issues.append("package_head_sha_mismatch")

    gate_sha = sudo_sha256(gate_path)
    if gate_sha != WITNESS_GATE_BUNDLE_SHA256:
        issues.append("gate_bundle_sha_mismatch")
    pkg_gate = package.get("gate") or {}
    if pkg_gate.get("bundle_sha256") != WITNESS_GATE_BUNDLE_SHA256:
        issues.append("package_gate_sha_mismatch")
    if abs(float(pkg_gate.get("threshold") or -1) - float(WITNESS_GATE_THRESHOLD)) > 1e-9:
        issues.append("gate_threshold_mismatch")

    enc = package.get("encoder") or {}
    if enc.get("state_hash") != EXPECTED_ENCODER_STATE_HASH:
        issues.append("encoder_state_hash_mismatch")
    if not exact_int_equals(enc.get("trainable_parameters"), 0):
        issues.append("encoder_trainable_nonzero")
    if enc.get("model_id") != SELECTED_ENCODER_MODEL_ID:
        issues.append("encoder_model_id_mismatch")
    if enc.get("revision") != SELECTED_ENCODER_REVISION:
        issues.append("encoder_revision_mismatch")

    th_live = threshold_manifest_payload()
    hier_live = hierarchy_constraints_payload()
    pkg_th = (package.get("thresholds") or {}).get("thresholds_ordered")
    live_th = th_live.get("thresholds_ordered")
    if pkg_th and pkg_th != live_th:
        issues.append("threshold_manifest_mismatch")
    pkg_rules = (package.get("hierarchy_constraints") or {}).get("rules")
    if pkg_rules != hier_live.get("rules"):
        issues.append("hierarchy_constraint_mismatch")

    # Gates frozen vs operating contract
    for k, v in OPERATING_QUALIFICATION_GATES.items():
        if k in {
            "system_macro_f1_min",
            "hierarchy_violation_max",
            "min_axis_macro_f1",
            "zero_label_false_positive_rate_max",
            "zero_label_exact_rejection_min",
            "positive_only_system_macro_f1_min",
        } and v != OPERATING_QUALIFICATION_GATES[k]:
            issues.append(f"gate_drift_{k}")

    ok = not issues
    return {
        "ok": ok,
        "issues": issues,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "seal_sha256": seal.get("seal_sha256"),
        "package_sha256": package.get("PACKAGE_SHA256"),
        "head_bundle_sha256": head_sha,
        "gate_bundle_sha256": gate_sha,
        "gate_threshold": pkg_gate.get("threshold"),
        "encoder_state_hash": enc.get("state_hash"),
        "encoder_model_id": enc.get("model_id"),
        "encoder_revision": enc.get("revision"),
        "encoder_trainable_parameters": enc.get("trainable_parameters"),
        "n_rows": n_lines,
        "forbidden_overlap": disjoint.get("forbidden_overlap"),
        "qualification_model_executions": seal.get("qualification_model_executions"),
        "qualification_state": seal.get("QUALIFICATION_STATE"),
        "threshold_manifest_sha_live": sha256_text(canonical_json(th_live)),
        "constraint_manifest_sha_live": sha256_text(canonical_json(hier_live)),
        "contract": execute_contract(),
        "package": package,
        "seal": seal,
    }


def error_decomposition(rows, result, vocabs):
    import numpy as np

    counts = Counter()
    tech = vocabs["domain"].index("domain.technology")
    ai = vocabs["domain"].index("domain.technology.ai_discourse")
    for i, r in enumerate(rows):
        for axis, key_fp, key_fn in (
            ("domain", "DOMAIN_FP", "DOMAIN_FN"),
            ("function", "FUNCTION_FP", "FUNCTION_FN"),
            ("mediation", "MEDIATION_FP", "MEDIATION_FN"),
        ):
            g = np.asarray(result["golds"][axis][i])
            p = np.asarray(result["preds"][axis][i])
            counts[key_fp] += int(((g == 0) & (p == 1)).sum())
            counts[key_fn] += int(((g == 1) & (p == 0)).sum())
        raw_d = np.asarray(result["preds_gated_pre_hier"]["domain"][i])
        if raw_d[ai] == 1 and raw_d[tech] == 0:
            counts["PARENT_CHILD_VIOLATION"] += 1
        g_sum = n_lab(r)
        p_sum = int(
            np.asarray(result["preds"]["domain"][i]).sum()
            + np.asarray(result["preds"]["function"][i]).sum()
            + np.asarray(result["preds"]["mediation"][i]).sum()
        )
        if g_sum == 0 and p_sum > 0:
            counts["FALSE_ACCEPT_ZERO"] += 1
        if g_sum > 0 and p_sum == 0:
            counts["FALSE_REJECT_POSITIVE"] += 1
        if result["gate_scores"][i] < 0.225 and g_sum > 0:
            counts["GATE_OVER_REJECT"] += 1
        if result["gate_scores"][i] >= 0.225 and g_sum == 0 and p_sum > 0:
            counts["GATE_UNDER_REJECT"] += 1
        if p_sum > g_sum + 1:
            counts["OVERPREDICTION"] += 1
    return {"counts": dict(counts)}


def main() -> int:
    import numpy as np
    import torch

    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
    from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
    from hyperlexical.classification_v6_data_foundation import utc_now_iso
    from hyperlexical.classification_v6_operating_pipeline_harden import (
        PACKAGE_ID,
        PIPELINE_CANDIDATE_ID,
        WITNESS_GATE_THRESHOLD,
    )
    from hyperlexical.classification_v6_qualification_execute_002 import (
        EXPECTED_ENCODER_STATE_HASH,
        EXPECTED_HEAD_BUNDLE_SHA256,
        classify_qual_label,
    )
    from hyperlexical.classification_v6_qualification_execute_003 import (
        EXPECTED_PACKAGE_SHA256,
        EXPECTED_SEAL_SHA256,
        EXPERIMENT_ID,
        PHASE_RULE,
        QUALIFICATION_ID,
        REP_REFERENCE_POSITIVE_ONLY,
        REP_REFERENCE_SYSTEM_MACRO_F1,
        REP_REFERENCE_ZERO_EXACT,
        REP_REFERENCE_ZERO_FP,
        RESULT_ID,
        classify_retention,
        decide_disposition,
        evaluate_operating_gates,
        execute_contract,
    )
    from hyperlexical.classification_v6_semantic_pipeline_harden import (
        BAKEOFF_THRESHOLDS,
        SELECTED_ENCODER_MODEL_ID,
        SELECTED_ENCODER_REVISION,
    )

    PRIVATE_EXEC.mkdir(mode=0o700, parents=True, exist_ok=True)
    contract = execute_contract()
    write_private(PRIVATE_EXEC / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    print("preflight", flush=True)
    pf = preflight()
    write_private(PRIVATE_EXEC / "PREFLIGHT.json", pf)
    write_repo(
        REPO_ART / "preflight.json",
        {k: v for k, v in pf.items() if k not in {"package", "seal", "contract"}},
    )
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
    thresholds = {a: list(BAKEOFF_THRESHOLDS[a]) for a in vocabs}
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")
    gate_th = float(WITNESS_GATE_THRESHOLD)

    rows = load_jsonl(PRIVATE_QUAL / "QUALIFICATION_ROWS.jsonl")
    assert len(rows) == pf["n_rows"]
    texts = [str(r.get("text") or "") for r in rows]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"cold_load device={device}", flush=True)

    heads_path = PRIVATE_PKG / "heads" / "axis_nonlinear_heads.pt"
    gate_path = PRIVATE_PKG / "heads" / "any_evidence_gate.pt"
    heads, _head_bundle, head_sha = load_heads(heads_path, vocabs, device)
    gate, _gate_bundle, gate_sha = load_gate(gate_path, device)
    if head_sha != EXPECTED_HEAD_BUNDLE_SHA256 or gate_sha != pf["gate_bundle_sha256"]:
        disposition = decide_disposition(
            preflight_ok=True, execution_ok=False, gate_pass=False
        )
        summary = {
            "QUALIFICATION_DISPOSITION": disposition["QUALIFICATION_DISPOSITION"],
            "NEXT_ACTION": disposition["NEXT_ACTION"],
            "reason": "runtime_bundle_sha_mismatch",
            "head_sha": head_sha,
            "gate_sha": gate_sha,
        }
        write_private(PRIVATE_EXEC / "SUMMARY.json", summary)
        print(json.dumps(summary, indent=2))
        return 2

    print("encode_qual_003_once", flush=True)
    X, enc_hash, n_train = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        texts,
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    if n_train != 0 or enc_hash != EXPECTED_ENCODER_STATE_HASH:
        disposition = decide_disposition(
            preflight_ok=True, execution_ok=False, gate_pass=False
        )
        summary = {
            "QUALIFICATION_DISPOSITION": disposition["QUALIFICATION_DISPOSITION"],
            "NEXT_ACTION": disposition["NEXT_ACTION"],
            "reason": "encoder_runtime_invalid",
            "encoder_hash": enc_hash,
            "trainable": n_train,
        }
        write_private(PRIVATE_EXEC / "SUMMARY.json", summary)
        print(json.dumps(summary, indent=2))
        return 2

    print("score_operating_pipeline_once", flush=True)
    result = run_gated_once(
        rows, X, heads, gate, gate_th, vocabs, thresholds, tech_idx, ai_idx, device
    )

    # Persist predictions
    pred_rows = []
    for i, r in enumerate(rows):
        adj = []
        gated_d = result["preds_gated_pre_hier"]["domain"][i]
        final_d = result["preds"]["domain"][i]
        if gated_d[ai_idx] == 1 and gated_d[tech_idx] == 0 and final_d[tech_idx] == 1:
            adj.append(
                {
                    "rule": "ai_discourse_requires_technology",
                    "action": "force_parent_positive",
                }
            )
        pred_rows.append(
            {
                "identity": r["identity"],
                "gate_score": float(result["gate_scores"][i]),
                "gate_reject": bool(result["gate_scores"][i] < gate_th),
                "raw_domain_scores": [float(x) for x in result["scores"]["domain"][i]],
                "raw_function_scores": [
                    float(x) for x in result["scores"]["function"][i]
                ],
                "raw_mediation_scores": [
                    float(x) for x in result["scores"]["mediation"][i]
                ],
                "pre_gate_domain_labels": [
                    vocabs["domain"][j]
                    for j, v in enumerate(result["preds_pre_gate"]["domain"][i])
                    if v == 1
                ],
                "constraint_adjustments": adj,
                "final_domain_labels": [
                    vocabs["domain"][j]
                    for j, v in enumerate(result["preds"]["domain"][i])
                    if v == 1
                ],
                "final_function_labels": [
                    vocabs["function"][j]
                    for j, v in enumerate(result["preds"]["function"][i])
                    if v == 1
                ],
                "final_mediation_labels": [
                    vocabs["mediation"][j]
                    for j, v in enumerate(result["preds"]["mediation"][i])
                    if v == 1
                ],
                "encoder_sha": enc_hash,
                "head_bundle_sha": head_sha,
                "gate_bundle_sha": gate_sha,
                "gate_threshold": gate_th,
                "package_sha": EXPECTED_PACKAGE_SHA256,
                "qual_seal_sha": EXPECTED_SEAL_SHA256,
            }
        )
    write_jsonl(PRIVATE_EXEC / "RAW_PREDICTIONS.jsonl", pred_rows)
    write_jsonl(
        PRIVATE_EXEC / "FINAL_PREDICTIONS.jsonl",
        [
            {
                "identity": r["identity"],
                "final_domain_labels": p["final_domain_labels"],
                "final_function_labels": p["final_function_labels"],
                "final_mediation_labels": p["final_mediation_labels"],
                "gate_reject": p["gate_reject"],
            }
            for r, p in zip(rows, pred_rows)
        ],
    )

    gate_eval = evaluate_operating_gates(
        system_macro_f1=result["system_macro_f1"],
        hierarchy_violation=result["post_constraint_hierarchy_violation_rate"],
        axis_macros=result["axis_macros"],
        zero_label_false_positive_rate=result["zero_label_false_positive_rate"],
        zero_label_exact_rejection=result["zero_label_exact_rejection"],
        positive_only_system_macro_f1=result["positive_only_system_macro_f1"],
        mean_predicted_labels_on_zero_gold=result[
            "mean_predicted_labels_on_zero_gold"
        ],
    )
    retention = classify_retention(
        result["system_macro_f1"], rep_macro=REP_REFERENCE_SYSTEM_MACRO_F1
    )
    retention["zero_fp"] = {
        "qual": result["zero_label_false_positive_rate"],
        "rep": REP_REFERENCE_ZERO_FP,
        "delta": result["zero_label_false_positive_rate"] - REP_REFERENCE_ZERO_FP,
    }
    retention["positive_only"] = {
        "qual": result["positive_only_system_macro_f1"],
        "rep": REP_REFERENCE_POSITIVE_ONLY,
        "delta": result["positive_only_system_macro_f1"] - REP_REFERENCE_POSITIVE_ONLY,
        "retention_ratio": result["positive_only_system_macro_f1"]
        / max(1e-12, REP_REFERENCE_POSITIVE_ONLY),
    }
    retention["zero_exact"] = {
        "qual": result["zero_label_exact_rejection"],
        "rep": REP_REFERENCE_ZERO_EXACT,
    }

    per_label = {}
    for axis, vocab in vocabs.items():
        for lab in vocab:
            q = result["packed_axes"][axis]["per_label"][lab]
            per_label[lab] = {
                "axis": axis,
                "QUAL_support": int(q["support"]),
                "precision": float(q["precision"]),
                "recall": float(q["recall"]),
                "QUAL_f1": float(q["f1"]),
                "class": classify_qual_label(
                    qual_f1=float(q["f1"]), support=int(q["support"])
                ),
            }

    # Cardinality slices (operating system macro)
    card_slices = {}
    for name, pred in (
        ("zero_label_gold", lambda r: n_lab(r) == 0),
        ("single_label", lambda r: n_lab(r) == 1),
        ("two_label", lambda r: n_lab(r) == 2),
        ("three_plus_label", lambda r: n_lab(r) >= 3),
        ("positive_only", lambda r: n_lab(r) > 0),
    ):
        idx = [i for i, r in enumerate(rows) if pred(r)]
        if not idx:
            card_slices[name] = {"n": 0, "system_macro_f1": None}
            continue
        card_slices[name] = {
            "n": len(idx),
            "system_macro_f1": float(
                sum(
                    macro_f1(
                        np.asarray(result["golds"][a])[idx],
                        np.asarray(result["preds"][a])[idx],
                    )
                    for a in vocabs
                )
                / len(vocabs)
            ),
        }

    errors = error_decomposition(rows, result, vocabs)
    disposition = decide_disposition(
        preflight_ok=True, execution_ok=True, gate_pass=bool(gate_eval["pass"])
    )

    # EVALUATION_SPENT transition
    spent_seal = dict(seal)
    spent_seal["QUALIFICATION_STATE"] = "EVALUATION_SPENT"
    spent_seal["evaluation_spent"] = "EVALUATION_SPENT"
    spent_seal["qualification_model_executions"] = 1
    spent_seal["qualification_disposition"] = disposition["QUALIFICATION_DISPOSITION"]
    spent_seal["spent_at"] = utc_now_iso()
    spent_seal["seal_sha256_pre_spend"] = EXPECTED_SEAL_SHA256
    write_private(PRIVATE_QUAL / "QUALIFICATION_SEAL.json", spent_seal)
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
        "system_macro_f1": result["system_macro_f1"],
        "sample_f1": result["sample_f1"],
        "jaccard": result["jaccard"],
        "DOMAIN_macro_f1": result["axis_macros"]["domain"],
        "FUNCTION_macro_f1": result["axis_macros"]["function"],
        "MEDIATION_macro_f1": result["axis_macros"]["mediation"],
        "hierarchy_violation_rate": result["post_constraint_hierarchy_violation_rate"],
        "raw_hierarchy_violation_rate": result["raw_hierarchy_violation_rate"],
        "zero_label_false_positive_rate": result["zero_label_false_positive_rate"],
        "zero_label_exact_rejection": result["zero_label_exact_rejection"],
        "mean_predicted_labels_on_zero_gold": result[
            "mean_predicted_labels_on_zero_gold"
        ],
        "positive_only_system_macro_f1": result["positive_only_system_macro_f1"],
        "false_reject_positive_rate": result["false_reject_positive_rate"],
        "n_gated_zero": result["n_gated_zero"],
    }

    receipt = {
        "RESULT_ID": RESULT_ID,
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
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
        "gate_bundle_sha": gate_sha,
        "gate_threshold": gate_th,
        "qualification_model_executions": 1,
        "n_rows": len(rows),
        "primary_metrics": primary,
        "per_label": per_label,
        "REP_V2_retention": retention,
        "cardinality_slices": card_slices,
        "error_decomposition": errors,
        "gate_results": gate_eval,
        "hierarchy": {
            "raw_violation_rate": result["raw_hierarchy_violation_rate"],
            "post_constraint_violation_rate": result[
                "post_constraint_hierarchy_violation_rate"
            ],
            "corrections": result["hierarchy_corrections"],
        },
        "QUALIFICATION_DISPOSITION": disposition["QUALIFICATION_DISPOSITION"],
        "RELEASE_ELIGIBLE": disposition["RELEASE_ELIGIBLE"],
        "HUB_PUBLISH_AUTHORIZED": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "V6_OPERATING_PIPELINE_CANDIDATE_MUTATED": False,
        "evaluation_spent": "EVALUATION_SPENT",
        "NEXT_ACTION": disposition["NEXT_ACTION"],
        "code_revision": code_revision(),
        "settled_at": utc_now_iso(),
        "preflight_ok": True,
        "execution_ok": True,
    }
    receipt["V6_QUALIFICATION_003_RESULT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in receipt.items()
                if k != "V6_QUALIFICATION_003_RESULT_SHA256"
            }
        )
    )
    write_private(PRIVATE_EXEC / "RECEIPT.json", receipt)
    write_private(PRIVATE_EXEC / "GATES.json", gate_eval)
    write_private(PRIVATE_EXEC / "PRIMARY_METRICS.json", primary)
    write_private(PRIVATE_EXEC / "PER_LABEL.json", per_label)
    write_private(PRIVATE_EXEC / "RETENTION.json", retention)
    write_private(PRIVATE_EXEC / "CARDINALITY_SLICES.json", card_slices)
    write_private(PRIVATE_EXEC / "ERROR_DECOMPOSITION.json", errors)
    write_repo(REPO_ART / "receipt.json", receipt)
    write_repo(REPO_ART / "RECEIPT.json", receipt)
    write_repo(REPO_ART / "gates.json", gate_eval)
    write_repo(REPO_ART / "primary_metrics.json", primary)
    write_repo(REPO_ART / "retention.json", retention)
    write_repo(
        SPEC / "classification-v6-qualification-execute-003-receipt-20261001.json",
        receipt,
    )

    summary = {
        "QUALIFICATION_DISPOSITION": disposition["QUALIFICATION_DISPOSITION"],
        "RELEASE_ELIGIBLE": disposition["RELEASE_ELIGIBLE"],
        "NEXT_ACTION": disposition["NEXT_ACTION"],
        "HUB_PUBLISH_AUTHORIZED": False,
        "MODEL_WIDE_BEST_MUTATED": False,
        "qualification_model_executions": 1,
        "evaluation_spent": "EVALUATION_SPENT",
        "n_rows": len(rows),
        "system_macro_f1": result["system_macro_f1"],
        "DOMAIN_macro_f1": result["axis_macros"]["domain"],
        "FUNCTION_macro_f1": result["axis_macros"]["function"],
        "MEDIATION_macro_f1": result["axis_macros"]["mediation"],
        "hierarchy_violation": result["post_constraint_hierarchy_violation_rate"],
        "zero_label_false_positive_rate": result["zero_label_false_positive_rate"],
        "zero_label_exact_rejection": result["zero_label_exact_rejection"],
        "mean_predicted_labels_on_zero_gold": result[
            "mean_predicted_labels_on_zero_gold"
        ],
        "positive_only_system_macro_f1": result["positive_only_system_macro_f1"],
        "sample_f1": result["sample_f1"],
        "jaccard": result["jaccard"],
        "REP_V2_system": REP_REFERENCE_SYSTEM_MACRO_F1,
        "REP_V2_zero_fp": REP_REFERENCE_ZERO_FP,
        "REP_V2_positive_only": REP_REFERENCE_POSITIVE_ONLY,
        "retention_band": retention["band"],
        "gate_pass": gate_eval["pass"],
        "package_sha256": EXPECTED_PACKAGE_SHA256,
        "qual_seal_sha256": EXPECTED_SEAL_SHA256,
        "receipt_sha256": receipt["V6_QUALIFICATION_003_RESULT_SHA256"],
    }
    write_private(PRIVATE_EXEC / "SUMMARY.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(REPO_ART / "summary.json", summary)

    md = f"""# EXECUTE_V6_QUALIFICATION_003_ONCE

```text
QUALIFICATION_DISPOSITION = {disposition['QUALIFICATION_DISPOSITION']}
RELEASE_ELIGIBLE = {disposition['RELEASE_ELIGIBLE']}
n_rows = {len(rows)}
model_executions = 1
evaluation_spent = EVALUATION_SPENT

system_macro_f1 = {result['system_macro_f1']:.4f}
DOMAIN = {result['axis_macros']['domain']:.4f}
FUNCTION = {result['axis_macros']['function']:.4f}
MEDIATION = {result['axis_macros']['mediation']:.4f}
hierarchy_violation = {result['post_constraint_hierarchy_violation_rate']:.4f}
zero_label_FP = {result['zero_label_false_positive_rate']:.4f}
zero_label_exact = {result['zero_label_exact_rejection']:.4f}
mean_pred_on_zero = {result['mean_predicted_labels_on_zero_gold']:.4f}
positive_only = {result['positive_only_system_macro_f1']:.4f}
sample_f1 = {result['sample_f1']:.4f}
jaccard = {result['jaccard']:.4f}

REP_V2 witness: system={REP_REFERENCE_SYSTEM_MACRO_F1:.3f} zero-FP={REP_REFERENCE_ZERO_FP:.3f} pos={REP_REFERENCE_POSITIVE_ONLY:.3f}
retention_band = {retention['band']}
gate_pass = {gate_eval['pass']}
NEXT_ACTION = {disposition['NEXT_ACTION']}
```

Operating package `{EXPECTED_PACKAGE_SHA256[:12]}…` cold-loaded once.
QUAL seal `{EXPECTED_SEAL_SHA256[:12]}…` spent. MODEL_WIDE_BEST unchanged.
HUB_PUBLISH_AUTHORIZED = false.
"""
    write_repo(SPEC / "classification-v6-qualification-execute-003-20261001.md", md)
    write_private(PRIVATE_EXEC / "POINTER.json", {
        "MODEL_WIDE_BEST_MUTATED": False,
        "V6_OPERATING_PIPELINE_CANDIDATE_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
    })
    write_repo(REPO_ART / "pointer.json", {
        "MODEL_WIDE_BEST_MUTATED": False,
        "V6_OPERATING_PIPELINE_CANDIDATE_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
    })

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if disposition["QUALIFICATION_DISPOSITION"] != "V6_QUALIFICATION_003_INVALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
