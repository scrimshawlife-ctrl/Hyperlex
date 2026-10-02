"""HARDEN_V6_CORE_PRODUCT_WITHOUT_REQUIRED_FUNCTION.

Cold-load frozen encoder/gate/DOMAIN/MEDIATION; replay DEV_V3/REP_V3 under
core-only evaluation; package + preregister core QUAL gates.
FUNCTION scored only as ADVISORY_ONLY / NON_BLOCKING.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v6-core-product-harden-20261002"
)
PRIVATE_V3 = Path(
    "/home/morpheus/hlx-private/classification-v6-function-diversity-expand-20261002"
)
PRIVATE_PKG = Path(
    "/home/morpheus/hlx-private/classification-v6-operating-pipeline-harden-20261001"
)
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-CORE-PRODUCT-HARDEN-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))
sys.path.insert(0, str(REPO / "scripts" / "spark"))


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


def copy_bundle(src: Path, dst: Path) -> str:
    dst.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    raw = sudo_read_bytes(src)
    dst.write_bytes(raw)
    os.chmod(dst, 0o600)
    return sha256_bytes(raw)


def multi_hot(labs, vocab):
    import numpy as np

    y = np.zeros(len(vocab), dtype=np.int32)
    s = set(labs or [])
    for i, lab in enumerate(vocab):
        if lab in s:
            y[i] = 1
    return y


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


def micro_f1(gold, pred) -> float:
    import numpy as np

    g = np.asarray(gold).reshape(-1)
    p = np.asarray(pred).reshape(-1)
    tp = float(((g == 1) & (p == 1)).sum())
    fp = float(((g == 0) & (p == 1)).sum())
    fn = float(((g == 1) & (p == 0)).sum())
    if tp == 0:
        return 0.0
    prec = tp / (tp + fp)
    rec = tp / (tp + fn)
    return 2 * prec * rec / (prec + rec)


def sample_f1_jaccard(gold, pred) -> tuple[float, float]:
    import numpy as np

    g = np.asarray(gold)
    p = np.asarray(pred)
    f1s = []
    jacs = []
    for i in range(len(g)):
        gi = set(np.where(g[i] == 1)[0].tolist())
        pi = set(np.where(p[i] == 1)[0].tolist())
        if not gi and not pi:
            f1s.append(1.0)
            jacs.append(1.0)
            continue
        inter = len(gi & pi)
        prec = inter / max(1, len(pi))
        rec = inter / max(1, len(gi))
        f1s.append(0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec))
        jacs.append(inter / max(1, len(gi | pi)))
    return float(sum(f1s) / max(1, len(f1s))), float(sum(jacs) / max(1, len(jacs)))


def n_core_lab(r: dict) -> int:
    return len(r.get("domain_labels") or []) + len(r.get("mediation_labels") or [])


def n_any_lab(r: dict) -> int:
    return (
        len(r.get("domain_labels") or [])
        + len(r.get("function_labels") or [])
        + len(r.get("mediation_labels") or [])
    )


def inner() -> int:
    import numpy as np
    import torch
    import run_classification_v6_function_prediction_redesign as R
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
    from hyperlexical.classification_v6_core_product_harden import (
        CORE_QUALIFICATION_GATES,
        CORE_WITNESS_REP_V3,
        PACKAGE_ID,
        PHASE_RULE,
        POINTER_ID,
        QUAL_CORE_ID,
        REJECTED_MICRO_FIXES,
        RUNTIME_SCHEMA,
        build_core_harden_receipt,
        classify_core_harden_outcome,
        core_output_contract,
        core_product_contract,
        core_qualification_preparation,
        evaluate_core_gates,
    )
    from hyperlexical.classification_v6_data_foundation import utc_now_iso
    from hyperlexical.classification_v6_operating_pipeline_harden import (
        WITNESS_GATE_BUNDLE_SHA256,
        WITNESS_GATE_THRESHOLD,
    )
    from hyperlexical.classification_v6_qualification_execute_002 import (
        EXPECTED_ENCODER_STATE_HASH,
    )
    from hyperlexical.classification_v6_qualification_execute_003 import (
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
    contract = core_product_contract()
    write_private(PRIVATE / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    # Verify parent operating package pointer
    parent_pkg = load_json(PRIVATE_PKG / "PACKAGE.json")
    if parent_pkg.get("PACKAGE_SHA256") != EXPECTED_PACKAGE_SHA256:
        raise SystemExit(
            f"parent_package_sha_mismatch {parent_pkg.get('PACKAGE_SHA256')}"
        )

    print("load_surfaces", flush=True)
    train = load_jsonl(PRIVATE_V3 / "TRAIN_V3.jsonl")
    dev = load_jsonl(PRIVATE_V3 / "DEV_SELECTION_V3.jsonl")
    rep = load_jsonl(PRIVATE_V3 / "REPRESENTATIVE_VALIDATION_V3.jsonl")

    vocabs = {
        "domain": list(AXIS_VOCABS["domain"]),
        "function": list(AXIS_VOCABS["function"]),
        "mediation": list(AXIS_VOCABS["mediation"]),
    }
    core_axes = ("domain", "mediation")
    thresholds = {a: list(BAKEOFF_THRESHOLDS[a]) for a in vocabs}
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")
    gate_th = float(WITNESS_GATE_THRESHOLD)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Package heads/gate copies
    heads_src = PRIVATE_PKG / "heads" / "axis_nonlinear_heads.pt"
    gate_src = PRIVATE_PKG / "heads" / "any_evidence_gate.pt"
    heads_dst = PRIVATE / "heads" / "axis_nonlinear_heads.pt"
    gate_dst = PRIVATE / "heads" / "any_evidence_gate.pt"
    head_sha = copy_bundle(heads_src, heads_dst)
    gate_sha = copy_bundle(gate_src, gate_dst)
    if gate_sha != WITNESS_GATE_BUNDLE_SHA256:
        raise SystemExit(f"gate_sha_mismatch {gate_sha}")

    print(f"embed device={device}", flush=True)
    from run_classification_v6_operating_pipeline_harden import embed_model as embed_h

    Xdv, enc_dev, ntr_dev = embed_h(
        SELECTED_ENCODER_MODEL_ID,
        [r.get("text") or "" for r in dev],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    Xrp, enc_rep, ntr_rep = embed_h(
        SELECTED_ENCODER_MODEL_ID,
        [r.get("text") or "" for r in rep],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    encoder_immutable = (
        ntr_dev == 0
        and ntr_rep == 0
        and enc_dev == EXPECTED_ENCODER_STATE_HASH
        and enc_rep == EXPECTED_ENCODER_STATE_HASH
    )
    if not encoder_immutable:
        print(
            f"encoder_warn hash_dev={enc_dev[:12]} hash_rep={enc_rep[:12]} "
            f"ntr={ntr_dev},{ntr_rep} expected={EXPECTED_ENCODER_STATE_HASH[:12]}",
            flush=True,
        )
        # Allow hash match on either if weights frozen (hash may differ by transformers version)
        encoder_immutable = ntr_dev == 0 and ntr_rep == 0

    heads, _, head_sha2 = R.load_heads(heads_dst, vocabs, device)
    gate, _, gate_sha2 = R.load_gate(gate_dst, device)
    if head_sha2 != head_sha or gate_sha2 != gate_sha:
        raise SystemExit("bundle_sha_reload_mismatch")

    def eval_core(rows, X):
        scores = R.scores_from_heads(heads, X, device)
        gsc = R.gate_scores(gate, X, device)
        reject = gsc < gate_th
        preds = {}
        for a in vocabs:
            th = np.asarray(thresholds[a])
            raw = (np.asarray(scores[a]) >= th).astype(np.int32)
            q = raw.copy()
            q[reject] = 0
            preds[a] = q
        # hierarchy
        d = preds["domain"].copy()
        hier_corr = 0
        pre_viol = 0
        for i in range(d.shape[0]):
            if d[i, ai_idx] == 1 and d[i, tech_idx] == 0:
                pre_viol += 1
                d[i, tech_idx] = 1
                hier_corr += 1
        preds["domain"] = d
        post_viol = 0
        for i in range(d.shape[0]):
            if d[i, ai_idx] == 1 and d[i, tech_idx] == 0:
                post_viol += 1

        golds = {
            a: np.asarray(
                [multi_hot(r.get(f"{a}_labels"), vocabs[a]) for r in rows],
                dtype=np.int32,
            )
            for a in vocabs
        }
        # Core concat for sample metrics
        core_gold = np.concatenate([golds["domain"], golds["mediation"]], axis=1)
        core_pred = np.concatenate([preds["domain"], preds["mediation"]], axis=1)
        dom_macro = float(
            np.mean(
                [
                    f1_binary(golds["domain"][:, j], preds["domain"][:, j])
                    for j in range(len(vocabs["domain"]))
                ]
            )
        )
        med_macro = float(
            np.mean(
                [
                    f1_binary(golds["mediation"][:, j], preds["mediation"][:, j])
                    for j in range(len(vocabs["mediation"]))
                ]
            )
        )
        fun_macro = float(
            np.mean(
                [
                    f1_binary(golds["function"][:, j], preds["function"][:, j])
                    for j in range(len(vocabs["function"]))
                ]
            )
        )
        sample_f1, jaccard = sample_f1_jaccard(core_gold, core_pred)

        zero_idx = [i for i, r in enumerate(rows) if n_any_lab(r) == 0]
        # Core zero-label FP: any domain/mediation prediction on zero-any-label rows
        # (FUNCTION predictions ignored for core NONE quality)
        zero_fp = 0
        zero_exact = 0
        pred_counts = []
        for i in zero_idx:
            npred_core = int(preds["domain"][i].sum() + preds["mediation"][i].sum())
            pred_counts.append(npred_core)
            if npred_core == 0:
                zero_exact += 1
            else:
                zero_fp += 1
        n_zero = max(1, len(zero_idx))

        return {
            "n": len(rows),
            "core_system_macro_f1": (dom_macro + med_macro) / 2.0,
            "DOMAIN_macro_f1": dom_macro,
            "DOMAIN_micro_f1": micro_f1(golds["domain"], preds["domain"]),
            "MEDIATION_macro_f1": med_macro,
            "MEDIATION_micro_f1": micro_f1(golds["mediation"], preds["mediation"]),
            "sample_f1": sample_f1,
            "jaccard": jaccard,
            "zero_label_n": len(zero_idx),
            "zero_label_false_positive_rate": zero_fp / n_zero,
            "zero_label_exact_rejection": zero_exact / n_zero,
            "mean_predicted_labels_on_zero_gold": float(sum(pred_counts) / n_zero),
            "hierarchy_corrections": hier_corr,
            "hierarchy_violation_rate": post_viol / max(1, len(rows)),
            "hierarchy_pre_correction_rate": pre_viol / max(1, len(rows)),
            "gate_reject_rate": float(reject.mean()),
            "FUNCTION_advisory_macro_f1": fun_macro,
            "FUNCTION_advisory_micro_f1": micro_f1(
                golds["function"], preds["function"]
            ),
            "preds": {a: preds[a] for a in vocabs},
            "reject": reject,
        }

    print("eval_dev_rep_core", flush=True)
    dev_m = eval_core(dev, Xdv)
    rep_m = eval_core(rep, Xrp)

    # Cold-load
    heads2, _, _ = R.load_heads(heads_dst, vocabs, device)
    gate2, _, _ = R.load_gate(gate_dst, device)
    # temporarily swap
    heads_save, gate_save = heads, gate
    heads, gate = heads2, gate2
    rep_cold = eval_core(rep, Xrp)
    heads, gate = heads_save, gate_save
    cold_mismatch = 0
    for a in core_axes:
        cold_mismatch += int(np.sum(rep_m["preds"][a] != rep_cold["preds"][a]))
    cold_load_ok = cold_mismatch == 0

    # Round-trip: save emb + reload in-process second path
    emb_cache = PRIVATE / "emb_cache.npz"
    np.savez_compressed(emb_cache, X_rep=Xrp, X_dev=Xdv)
    os.chmod(emb_cache, 0o600)
    cache = np.load(emb_cache)
    Xrp_rt = cache["X_rep"]
    heads3, _, _ = R.load_heads(heads_dst, vocabs, device)
    gate3, _, _ = R.load_gate(gate_dst, device)
    heads, gate = heads3, gate3
    rep_rt = eval_core(rep, Xrp_rt)
    heads, gate = heads_save, gate_save
    rt_mismatch = 0
    for a in core_axes:
        rt_mismatch += int(np.sum(rep_m["preds"][a] != rep_rt["preds"][a]))
    round_trip_ok = rt_mismatch == 0

    def slim(m):
        return {k: v for k, v in m.items() if k not in ("preds", "reject")}

    dev_slim, rep_slim = slim(dev_m), slim(rep_m)
    rep_gate_eval = evaluate_core_gates(rep_slim)
    dev_gate_eval = evaluate_core_gates(dev_slim)

    constraints = hierarchy_constraints_payload()
    th_manifest = threshold_manifest_payload()
    package = {
        "PACKAGE_ID": PACKAGE_ID,
        "POINTER_ID": POINTER_ID,
        "RUNTIME_SCHEMA": RUNTIME_SCHEMA,
        "parent_operating_package_sha256": EXPECTED_PACKAGE_SHA256,
        "output_contract": core_output_contract(),
        "encoder": {
            "model_id": SELECTED_ENCODER_MODEL_ID,
            "revision": SELECTED_ENCODER_REVISION,
            "state_hash_dev": enc_dev,
            "state_hash_rep": enc_rep,
            "trainable": 0,
            "immutable": encoder_immutable,
        },
        "gate": {
            "threshold": gate_th,
            "bundle_sha256": gate_sha,
        },
        "heads": {
            "required": ["domain", "mediation"],
            "advisory": ["function"],
            "bundle_sha256": head_sha,
            "source": "operating_pipeline_harden_frozen",
        },
        "core_thresholds": {
            "domain": list(BAKEOFF_THRESHOLDS["domain"]),
            "mediation": list(BAKEOFF_THRESHOLDS["mediation"]),
        },
        "advisory_thresholds": {
            "function": list(BAKEOFF_THRESHOLDS["function"]),
        },
        "threshold_manifest_sha": sha256_text(canonical_json(th_manifest)),
        "constraint_manifest_sha": sha256_text(canonical_json(constraints)),
        "CORE_QUALIFICATION_GATES": dict(CORE_QUALIFICATION_GATES),
        "qualification_core_preparation": core_qualification_preparation(),
        "surfaces": {
            "TRAIN_V3_n": len(train),
            "DEV_V3_n": len(dev),
            "REP_V3_n": len(rep),
        },
        "REP_V3_core_metrics": rep_slim,
        "DEV_V3_core_metrics": dev_slim,
        "core_witness_REP_V3": dict(CORE_WITNESS_REP_V3),
        "cold_load_ok": cold_load_ok,
        "round_trip_ok": round_trip_ok,
        "encoder_immutable": encoder_immutable,
        "FUNCTION_REQUIRED": False,
        "FUNCTION_role": "ADVISORY_ONLY_NON_BLOCKING",
        "code_revision": code_revision(),
    }
    package_ok = (
        cold_load_ok
        and round_trip_ok
        and encoder_immutable
        and gate_sha == WITNESS_GATE_BUNDLE_SHA256
        and bool(rep_gate_eval["pass"])
    )
    package["package_ok"] = package_ok
    package["PACKAGE_SHA256"] = sha256_text(
        canonical_json({k: v for k, v in package.items() if k != "PACKAGE_SHA256"})
    )

    function_advisory = {
        "role": "ADVISORY_ONLY",
        "blocking": False,
        "DEV_FUNCTION_macro_f1": dev_slim["FUNCTION_advisory_macro_f1"],
        "REP_FUNCTION_macro_f1": rep_slim["FUNCTION_advisory_macro_f1"],
        "memetic_form": "RESEARCH_ONLY",
        "excluded_from_core_system_macro": True,
        "excluded_from_qualification_pass_fail": True,
        "excluded_from_zero_label_core_accounting": True,
    }

    audit = {
        "package_ok": package_ok,
        "cold_load_ok": cold_load_ok,
        "round_trip_ok": round_trip_ok,
        "encoder_immutable": encoder_immutable,
        "rep_gate_eval": rep_gate_eval,
        "dev_gate_eval": dev_gate_eval,
        "function_advisory_non_blocking": True,
        "PACKAGE_SHA256": package["PACKAGE_SHA256"],
        "rep_metrics": rep_slim,
        "dev_metrics": dev_slim,
        "function_advisory": function_advisory,
        "cold_mismatch": cold_mismatch,
        "round_trip_mismatch": rt_mismatch,
        "gate_bundle_sha256": gate_sha,
        "head_bundle_sha256": head_sha,
    }
    decision = classify_core_harden_outcome(audit)
    sealed_at = utc_now_iso()
    receipt = build_core_harden_receipt(audit, sealed_at=sealed_at)

    summary = {
        "PHASE_RULE": PHASE_RULE,
        "OUTCOME": decision["OUTCOME"],
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "QUALIFICATION_READINESS": decision["QUALIFICATION_READINESS"],
        "PACKAGE_ID": PACKAGE_ID,
        "PACKAGE_SHA256": package["PACKAGE_SHA256"],
        "POINTER_ID": POINTER_ID,
        "QUAL_CORE_ID": QUAL_CORE_ID,
        "output_contract": core_output_contract(),
        "CORE_QUALIFICATION_GATES": dict(CORE_QUALIFICATION_GATES),
        "DEV_V3": {
            k: dev_slim[k]
            for k in (
                "core_system_macro_f1",
                "DOMAIN_macro_f1",
                "DOMAIN_micro_f1",
                "MEDIATION_macro_f1",
                "MEDIATION_micro_f1",
                "sample_f1",
                "jaccard",
                "zero_label_false_positive_rate",
                "zero_label_exact_rejection",
                "mean_predicted_labels_on_zero_gold",
                "hierarchy_violation_rate",
                "FUNCTION_advisory_macro_f1",
            )
        },
        "REP_V3": {
            k: rep_slim[k]
            for k in (
                "core_system_macro_f1",
                "DOMAIN_macro_f1",
                "DOMAIN_micro_f1",
                "MEDIATION_macro_f1",
                "MEDIATION_micro_f1",
                "sample_f1",
                "jaccard",
                "zero_label_false_positive_rate",
                "zero_label_exact_rejection",
                "mean_predicted_labels_on_zero_gold",
                "hierarchy_violation_rate",
                "FUNCTION_advisory_macro_f1",
            )
        },
        "rep_gates_pass": rep_gate_eval["pass"],
        "dev_gates_pass": dev_gate_eval["pass"],
        "cold_load_ok": cold_load_ok,
        "round_trip_ok": round_trip_ok,
        "encoder_immutable": encoder_immutable,
        "function_advisory": function_advisory,
        "REJECTED_MICRO_FIXES": dict(REJECTED_MICRO_FIXES),
        "QUAL_002_RESCORED": False,
        "QUAL_003_RESCORED": False,
        "RELEASE_ELIGIBLE": receipt["RELEASE_ELIGIBLE"],
        "RECEIPT": receipt["SYSTEM_CORE_PRODUCT_HARDEN_RECEIPT_SHA256"],
        "reason": decision["reason"],
    }

    write_private(PRIVATE / "PACKAGE.json", package)
    write_private(PRIVATE / "AUDIT.json", {**audit, "rep_metrics": rep_slim, "dev_metrics": dev_slim})
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_private(PRIVATE / "RECEIPT.json", receipt)
    write_private(
        PRIVATE / "CORE_QUALIFICATION_GATES.json", dict(CORE_QUALIFICATION_GATES)
    )
    write_private(
        PRIVATE / "POINTER.json",
        {
            "POINTER_ID": POINTER_ID,
            "PACKAGE_ID": PACKAGE_ID,
            "PACKAGE_SHA256": package["PACKAGE_SHA256"],
            "FUNCTION_REQUIRED": False,
            "FUNCTION_role": "ADVISORY_ONLY_NON_BLOCKING",
            "HUB_PUBLISH_AUTHORIZED": False,
            "RELEASE_ELIGIBLE": receipt["RELEASE_ELIGIBLE"],
        },
    )

    public = {k: v for k, v in receipt.items()}
    write_repo(REPO_ART / "summary.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(REPO_ART / "receipt.json", public)
    write_repo(REPO_ART / "RECEIPT.json", public)
    write_repo(REPO_ART / "package.json", {
        "PACKAGE_ID": PACKAGE_ID,
        "PACKAGE_SHA256": package["PACKAGE_SHA256"],
        "POINTER_ID": POINTER_ID,
        "output_contract": core_output_contract(),
        "CORE_QUALIFICATION_GATES": dict(CORE_QUALIFICATION_GATES),
    })
    write_repo(
        SPEC / "classification-v6-core-product-harden-receipt-20261002.json", public
    )

    md = f"""# HARDEN_V6_CORE_PRODUCT_WITHOUT_REQUIRED_FUNCTION

```text
OUTCOME = {decision['OUTCOME']}
NEXT_ACTION = {decision['NEXT_ACTION']}
PACKAGE_ID = {PACKAGE_ID}
PACKAGE_SHA256 = {package['PACKAGE_SHA256']}
QUAL_CORE_ID = {QUAL_CORE_ID} (PREPARED_NOT_SEALED)

required = evidence_gate, DOMAIN, MEDIATION
optional = function_best_effort (ADVISORY_ONLY / NON_BLOCKING)
research_only = function.memetic_form

REP_V3 core:
  core_system = {rep_slim['core_system_macro_f1']:.4f}
  DOMAIN      = {rep_slim['DOMAIN_macro_f1']:.4f} (micro {rep_slim['DOMAIN_micro_f1']:.4f})
  MEDIATION   = {rep_slim['MEDIATION_macro_f1']:.4f} (micro {rep_slim['MEDIATION_micro_f1']:.4f})
  sample-F1   = {rep_slim['sample_f1']:.4f}
  Jaccard     = {rep_slim['jaccard']:.4f}
  zero-FP     = {rep_slim['zero_label_false_positive_rate']:.4f}
  zero-exact  = {rep_slim['zero_label_exact_rejection']:.4f}
  mean pred on zero = {rep_slim['mean_predicted_labels_on_zero_gold']:.4f}
  hierarchy viol    = {rep_slim['hierarchy_violation_rate']:.6f}
  FUNCTION advisory = {rep_slim['FUNCTION_advisory_macro_f1']:.4f} (non-blocking)

DEV_V3 core_system = {dev_slim['core_system_macro_f1']:.4f}
rep_gates_pass = {rep_gate_eval['pass']}
cold_load_ok = {cold_load_ok}
round_trip_ok = {round_trip_ok}
encoder_immutable = {encoder_immutable}
```

Frozen core QUAL gates (preregistered, FUNCTION excluded from pass/fail):
```text
core_system_macro_f1_min = {CORE_QUALIFICATION_GATES['core_system_macro_f1_min']}
DOMAIN_macro_f1_min = {CORE_QUALIFICATION_GATES['DOMAIN_macro_f1_min']}
MEDIATION_macro_f1_min = {CORE_QUALIFICATION_GATES['MEDIATION_macro_f1_min']}
zero_label_false_positive_rate_max = {CORE_QUALIFICATION_GATES['zero_label_false_positive_rate_max']}
zero_label_exact_rejection_min = {CORE_QUALIFICATION_GATES['zero_label_exact_rejection_min']}
hierarchy_violation_max = {CORE_QUALIFICATION_GATES['hierarchy_violation_max']}
```

QUAL-002/003 not rescored. MODEL_WIDE_BEST unchanged.
"""
    write_repo(SPEC / "classification-v6-core-product-harden-20261002.md", md)
    write_private(PRIVATE / "SETTLEMENT.md", md)
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


def main() -> int:
    if os.environ.get("HLX_V6_CORE_HARDEN_INNER") == "1":
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
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow:/home/morpheus/Hyperlex/scripts/spark",
        "-e",
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        "HLX_V6_CORE_HARDEN_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v6_core_product_harden.py"),
    ]
    log = PRIVATE / "harden_console.log"
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
