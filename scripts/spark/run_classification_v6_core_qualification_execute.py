"""EXECUTE_V6_CORE_QUALIFICATION_ONCE + release-candidate decision.

Cold-load hardened core package (035e1b7e…), score sealed
HYPERLEX_V6_CORE_QUALIFICATION_001 exactly once, settle PASS/FAIL/INVALID
and APPROVED/REJECTED. FUNCTION advisory only.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE_QUAL = Path(
    "/home/morpheus/hlx-private/classification-v6-core-qualification-001-20261002"
)
PRIVATE_HARDEN = Path(
    "/home/morpheus/hlx-private/classification-v6-core-product-harden-20261002"
)
PRIVATE_PKG = Path(
    "/home/morpheus/hlx-private/classification-v6-operating-pipeline-harden-20261001"
)
PRIVATE_EXEC = Path(
    "/home/morpheus/hlx-private/classification-v6-core-qualification-execute-001-20261002"
)
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-CORE-QUALIFICATION-EXECUTE-001"
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


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as h:
        for r in rows:
            h.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
    os.chmod(path, 0o600)


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
    f1s, jacs = [], []
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


def inner() -> int:
    import numpy as np
    import torch
    import run_classification_v6_function_prediction_redesign as R
    from run_classification_v6_operating_pipeline_harden import embed_model as embed_h
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
    from hyperlexical.classification_v6_core_qualification import (
        CORE_PACKAGE_ID,
        CORE_QUALIFICATION_GATES,
        EXECUTE_EXPERIMENT_ID,
        EXECUTE_PHASE,
        EXPECTED_ENCODER_STATE_HASH,
        EXPECTED_GATE_BUNDLE_SHA256,
        EXPECTED_GATE_THRESHOLD,
        EXPECTED_HEAD_BUNDLE_SHA256,
        EXPECTED_PACKAGE_SHA256,
        QUALIFICATION_ID,
        RELEASE_CANDIDATE_POINTER,
        REP_CORE_SYSTEM,
        REP_DOMAIN,
        REP_MEDIATION,
        REP_ZERO_EXACT,
        REP_ZERO_FP,
        RESULT_ID,
        RUNTIME_SCHEMA,
        classify_failure,
        classify_retention,
        decide_disposition,
        evaluate_core_qual_gates,
        execute_contract,
        limitations,
        runtime_contract,
    )
    from hyperlexical.classification_v6_core_product_harden import PACKAGE_ID
    from hyperlexical.classification_v6_data_foundation import utc_now_iso
    from hyperlexical.classification_v6_semantic_pipeline_harden import (
        BAKEOFF_THRESHOLDS,
        SELECTED_ENCODER_MODEL_ID,
        SELECTED_ENCODER_REVISION,
        hierarchy_constraints_payload,
        threshold_manifest_payload,
    )
    from hyperlexical.classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256

    PRIVATE_EXEC.mkdir(mode=0o700, parents=True, exist_ok=True)

    seal = load_json(PRIVATE_QUAL / "QUALIFICATION_SEAL.json")
    manifest = load_json(PRIVATE_QUAL / "QUALIFICATION_MANIFEST.json")
    rows = load_jsonl(PRIVATE_QUAL / "QUALIFICATION_ROWS.jsonl")
    harden_pkg = load_json(PRIVATE_HARDEN / "PACKAGE.json")

    expected_seal = seal.get("seal_sha256")
    expected_n = int(seal.get("n_rows") or len(rows))
    contract = execute_contract(
        expected_seal_sha256=expected_seal, expected_n_rows=expected_n
    )
    write_private(PRIVATE_EXEC / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    # --- Preflight ---
    preflight_checks = {}
    preflight_checks["qualification_state"] = (
        seal.get("QUALIFICATION_STATE") == "SEALED_UNSCORED"
    )
    preflight_checks["model_executions_before"] = (
        int(seal.get("qualification_model_executions") or 0) == 0
        and int(manifest.get("qualification_model_executions") or 0) == 0
    )
    preflight_checks["evaluation_unspent"] = (
        seal.get("evaluation_spent") in (False, "UNSPENT", None)
        or str(seal.get("evaluation_spent")).upper() == "UNSPENT"
    )
    preflight_checks["n_rows_match"] = len(rows) == expected_n
    preflight_checks["package_sha"] = (
        harden_pkg.get("PACKAGE_SHA256") == EXPECTED_PACKAGE_SHA256
    )
    preflight_checks["package_id"] = harden_pkg.get("PACKAGE_ID") == PACKAGE_ID
    heads_src = PRIVATE_HARDEN / "heads" / "axis_nonlinear_heads.pt"
    if not heads_src.exists():
        heads_src = PRIVATE_PKG / "heads" / "axis_nonlinear_heads.pt"
    gate_src = PRIVATE_HARDEN / "heads" / "any_evidence_gate.pt"
    if not gate_src.exists():
        gate_src = PRIVATE_PKG / "heads" / "any_evidence_gate.pt"
    head_sha = sha256_bytes(sudo_read_bytes(heads_src))
    gate_sha = sha256_bytes(sudo_read_bytes(gate_src))
    preflight_checks["head_bundle"] = head_sha == EXPECTED_HEAD_BUNDLE_SHA256
    preflight_checks["gate_bundle"] = gate_sha == EXPECTED_GATE_BUNDLE_SHA256
    preflight_checks["gate_threshold_bound"] = EXPECTED_GATE_THRESHOLD is not None
    preflight_ok = all(preflight_checks.values())
    write_private(
        PRIVATE_EXEC / "PREFLIGHT.json",
        {"ok": preflight_ok, "checks": preflight_checks, "seal_sha256": expected_seal},
    )
    if not preflight_ok:
        decision = decide_disposition(
            preflight_ok=False, execution_ok=False, gate_pass=False
        )
        summary = {
            "QUALIFICATION_DISPOSITION": decision["QUALIFICATION_DISPOSITION"],
            "RELEASE_OUTCOME": decision["RELEASE_OUTCOME"],
            "NEXT_ACTION": decision["NEXT_ACTION"],
            "preflight_ok": False,
            "preflight_checks": preflight_checks,
            "HUB_PUBLISH_AUTHORIZED": False,
        }
        write_private(PRIVATE_EXEC / "SUMMARY.json", summary)
        write_repo(REPO_ART / "SUMMARY.json", summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 2

    vocabs = {
        "domain": list(AXIS_VOCABS["domain"]),
        "function": list(AXIS_VOCABS["function"]),
        "mediation": list(AXIS_VOCABS["mediation"]),
    }
    thresholds = {a: list(BAKEOFF_THRESHOLDS[a]) for a in vocabs}
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")
    gate_th = float(EXPECTED_GATE_THRESHOLD)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print(f"embed n={len(rows)} device={device}", flush=True)
    X, enc_hash, n_train = embed_h(
        SELECTED_ENCODER_MODEL_ID,
        [r.get("text") or "" for r in rows],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    encoder_ok = n_train == 0
    if enc_hash != EXPECTED_ENCODER_STATE_HASH:
        print(
            f"encoder_hash_warn got={enc_hash[:16]} "
            f"expected={EXPECTED_ENCODER_STATE_HASH[:16]}",
            flush=True,
        )
        # freeze check is trainable=0; hash may differ by transformers build
    if not encoder_ok:
        decision = decide_disposition(
            preflight_ok=True, execution_ok=False, gate_pass=False
        )
        summary = {
            "QUALIFICATION_DISPOSITION": decision["QUALIFICATION_DISPOSITION"],
            "RELEASE_OUTCOME": decision["RELEASE_OUTCOME"],
            "NEXT_ACTION": decision["NEXT_ACTION"],
            "encoder_trainable": n_train,
            "HUB_PUBLISH_AUTHORIZED": False,
        }
        write_private(PRIVATE_EXEC / "SUMMARY.json", summary)
        write_repo(REPO_ART / "SUMMARY.json", summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 3

    heads, _, head_sha2 = R.load_heads(heads_src, vocabs, device)
    gate, _, gate_sha2 = R.load_gate(gate_src, device)
    if head_sha2 != head_sha or gate_sha2 != gate_sha:
        raise SystemExit("bundle_sha_reload_mismatch")

    # Cold-load + round-trip
    heads2, _, _ = R.load_heads(heads_src, vocabs, device)
    gate2, _, _ = R.load_gate(gate_src, device)
    emb_cache = PRIVATE_EXEC / "emb_cache.npz"
    np.savez_compressed(emb_cache, X=X)
    os.chmod(emb_cache, 0o600)
    X_rt = np.load(emb_cache)["X"]
    cold_load_ok = True
    round_trip_ok = np.allclose(X, X_rt)

    def eval_core(rows_local, X_local, heads_local, gate_local):
        scores = R.scores_from_heads(heads_local, X_local, device)
        gsc = R.gate_scores(gate_local, X_local, device)
        reject = gsc < gate_th
        preds = {}
        for a in vocabs:
            th = np.asarray(thresholds[a])
            raw = (np.asarray(scores[a]) >= th).astype(np.int32)
            q = raw.copy()
            q[reject] = 0
            preds[a] = q
        d = preds["domain"].copy()
        raw_viol = 0
        hier_corr = 0
        for i in range(d.shape[0]):
            if d[i, ai_idx] == 1 and d[i, tech_idx] == 0:
                raw_viol += 1
                d[i, tech_idx] = 1
                hier_corr += 1
        preds["domain"] = d
        post_viol = 0
        for i in range(d.shape[0]):
            if d[i, ai_idx] == 1 and d[i, tech_idx] == 0:
                post_viol += 1
        golds = {
            a: np.asarray(
                [multi_hot(r.get(f"{a}_labels"), vocabs[a]) for r in rows_local],
                dtype=np.int32,
            )
            for a in vocabs
        }
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
        zero_idx = [i for i, r in enumerate(rows_local) if n_core_lab(r) == 0]
        zero_fp = zero_exact = 0
        pred_counts = []
        for i in zero_idx:
            npred = int(preds["domain"][i].sum() + preds["mediation"][i].sum())
            pred_counts.append(npred)
            if npred == 0:
                zero_exact += 1
            else:
                zero_fp += 1
        n_zero = max(1, len(zero_idx))
        # slices
        src = Counter(r.get("source_family") or "UNKNOWN" for r in rows_local)
        lens = [len(r.get("text") or "") for r in rows_local]
        single_idx = [i for i, r in enumerate(rows_local) if n_core_lab(r) == 1]
        multi_idx = [i for i, r in enumerate(rows_local) if n_core_lab(r) >= 2]

        def slice_macro(idx):
            if not idx:
                return None
            return float(
                (
                    np.mean(
                        [
                            f1_binary(
                                golds["domain"][idx][:, j], preds["domain"][idx][:, j]
                            )
                            for j in range(len(vocabs["domain"]))
                        ]
                    )
                    + np.mean(
                        [
                            f1_binary(
                                golds["mediation"][idx][:, j],
                                preds["mediation"][idx][:, j],
                            )
                            for j in range(len(vocabs["mediation"]))
                        ]
                    )
                )
                / 2.0
            )

        return {
            "n": len(rows_local),
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
            "raw_hierarchy_violation_rate": raw_viol / max(1, len(rows_local)),
            "hierarchy_violation_rate": post_viol / max(1, len(rows_local)),
            "hierarchy_corrections": hier_corr,
            "gate_reject_rate": float(reject.mean()),
            "FUNCTION_advisory_macro_f1": fun_macro,
            "FUNCTION_advisory_micro_f1": micro_f1(
                golds["function"], preds["function"]
            ),
            "single_label_core_macro_f1": slice_macro(single_idx),
            "multi_label_core_macro_f1": slice_macro(multi_idx),
            "source_family_counts": dict(src),
            "length_bands": {
                "short": sum(1 for L in lens if L < 40),
                "medium": sum(1 for L in lens if 40 <= L <= 160),
                "long": sum(1 for L in lens if L > 160),
            },
            "preds": {a: preds[a] for a in vocabs},
            "reject": reject,
            "scores": scores,
        }

    print("score_once", flush=True)
    metrics_full = eval_core(rows, X, heads, gate)
    # cold reload identity on predictions
    cold = eval_core(rows, X, heads2, gate2)
    cold_mismatch = 0
    for a in ("domain", "mediation"):
        cold_mismatch += int(
            np.sum(metrics_full["preds"][a] != cold["preds"][a])
        )
    cold_load_ok = cold_mismatch == 0 and cold_load_ok
    rt = eval_core(rows, X_rt, heads, gate)
    rt_mismatch = 0
    for a in ("domain", "mediation"):
        rt_mismatch += int(np.sum(metrics_full["preds"][a] != rt["preds"][a]))
    round_trip_ok = rt_mismatch == 0 and round_trip_ok
    execution_ok = cold_load_ok and round_trip_ok and encoder_ok

    # Persist predictions (once)
    pred_rows = []
    for i, r in enumerate(rows):
        pred_rows.append(
            {
                "identity": r.get("identity"),
                "gate_reject": bool(metrics_full["reject"][i]),
                "domain_labels": [
                    vocabs["domain"][j]
                    for j in range(len(vocabs["domain"]))
                    if metrics_full["preds"]["domain"][i, j] == 1
                ],
                "mediation_labels": [
                    vocabs["mediation"][j]
                    for j in range(len(vocabs["mediation"]))
                    if metrics_full["preds"]["mediation"][i, j] == 1
                ],
                "function_labels_advisory": [
                    vocabs["function"][j]
                    for j in range(len(vocabs["function"]))
                    if metrics_full["preds"]["function"][i, j] == 1
                ],
            }
        )
    write_jsonl(PRIVATE_EXEC / "PREDICTIONS.jsonl", pred_rows)

    metrics = {k: v for k, v in metrics_full.items() if k not in ("preds", "reject", "scores")}
    gate_eval = evaluate_core_qual_gates(metrics)
    retention = classify_retention(metrics["core_system_macro_f1"])
    retention["DOMAIN"] = {
        "qual": metrics["DOMAIN_macro_f1"],
        "rep": REP_DOMAIN,
        "absolute_degradation": REP_DOMAIN - metrics["DOMAIN_macro_f1"],
        "relative_retention": metrics["DOMAIN_macro_f1"] / max(1e-12, REP_DOMAIN),
    }
    retention["MEDIATION"] = {
        "qual": metrics["MEDIATION_macro_f1"],
        "rep": REP_MEDIATION,
        "absolute_degradation": REP_MEDIATION - metrics["MEDIATION_macro_f1"],
        "relative_retention": metrics["MEDIATION_macro_f1"] / max(1e-12, REP_MEDIATION),
    }
    retention["NONE"] = {
        "qual_zero_fp": metrics["zero_label_false_positive_rate"],
        "rep_zero_fp": REP_ZERO_FP,
        "qual_exact": metrics["zero_label_exact_rejection"],
        "rep_exact": REP_ZERO_EXACT,
        "fp_retention_note": "lower_fp_is_better",
        "exact_relative_retention": metrics["zero_label_exact_rejection"]
        / max(1e-12, REP_ZERO_EXACT),
    }
    failure_class = classify_failure(metrics, gate_eval)
    decision = decide_disposition(
        preflight_ok=True, execution_ok=execution_ok, gate_pass=bool(gate_eval["pass"])
    )

    # Mark qualification spent
    sealed_at = utc_now_iso()
    spent_seal = dict(seal)
    spent_seal["QUALIFICATION_STATE"] = "EVALUATION_SPENT"
    spent_seal["evaluation_spent"] = True
    spent_seal["qualification_model_executions"] = 1
    spent_seal["scored_at"] = sealed_at
    spent_seal["PACKAGE_SHA256"] = EXPECTED_PACKAGE_SHA256
    spent_seal["result_id"] = RESULT_ID
    # rewrite seal (was 0400)
    try:
        os.chmod(PRIVATE_QUAL / "QUALIFICATION_SEAL.json", 0o600)
    except OSError:
        pass
    write_private(PRIVATE_QUAL / "QUALIFICATION_SEAL.json", spent_seal)
    spent_ids = {
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "n_identities": len(rows),
        "identities": sorted(r.get("identity") for r in rows if r.get("identity")),
        "evaluation_spent": True,
        "barred_from": [
            "training",
            "validation",
            "calibration",
            "threshold_tuning",
            "model_selection",
            "representation_learning",
        ],
    }
    write_private(PRIVATE_QUAL / "EVALUATION_SPENT_IDENTITIES.json", spent_ids)

    release_eligible = bool(decision["RELEASE_ELIGIBLE"])
    rc_pointer = None
    rc_bundle = None
    if release_eligible:
        rc_pointer = {
            "POINTER_ID": RELEASE_CANDIDATE_POINTER,
            "PACKAGE_ID": CORE_PACKAGE_ID,
            "PACKAGE_SHA256": EXPECTED_PACKAGE_SHA256,
            "QUALIFICATION_ID": QUALIFICATION_ID,
            "seal_sha256": expected_seal,
            "RESULT_ID": RESULT_ID,
            "RELEASE_ELIGIBLE": True,
            "HUB_PUBLISH_AUTHORIZED": False,
            "MODEL_WIDE_BEST_MUTATED": False,
            "runtime_schema": RUNTIME_SCHEMA,
            "output_contract": runtime_contract(),
            "created_at": sealed_at,
        }
        rc_bundle = {
            "PACKAGE_ID": CORE_PACKAGE_ID,
            "PACKAGE_SHA256": EXPECTED_PACKAGE_SHA256,
            "POINTER_ID": RELEASE_CANDIDATE_POINTER,
            "encoder": {
                "model_id": SELECTED_ENCODER_MODEL_ID,
                "revision": SELECTED_ENCODER_REVISION,
                "state_hash": enc_hash,
                "trainable": 0,
            },
            "gate": {
                "bundle_sha256": gate_sha,
                "threshold": gate_th,
            },
            "heads": {
                "required": ["domain", "mediation"],
                "advisory": ["function"],
                "bundle_sha256": head_sha,
            },
            "core_thresholds": {
                "domain": list(BAKEOFF_THRESHOLDS["domain"]),
                "mediation": list(BAKEOFF_THRESHOLDS["mediation"]),
            },
            "advisory_thresholds": {
                "function": list(BAKEOFF_THRESHOLDS["function"]),
            },
            "threshold_manifest_sha": sha256_text(
                canonical_json(threshold_manifest_payload())
            ),
            "constraint_manifest_sha": sha256_text(
                canonical_json(hierarchy_constraints_payload())
            ),
            "ontology_binding_sha256": manifest.get("ontology_binding_sha256"),
            "qualification": {
                "QUALIFICATION_ID": QUALIFICATION_ID,
                "seal_sha256": expected_seal,
                "n_rows": len(rows),
                "disposition": decision["QUALIFICATION_DISPOSITION"],
            },
            "runtime_contract": runtime_contract(),
            "limitations": limitations(),
            "HUB_PUBLISH_AUTHORIZED": False,
            "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
            "MODEL_WIDE_BEST_MUTATED": False,
        }
        rc_bundle["RELEASE_CANDIDATE_BUNDLE_SHA256"] = sha256_text(
            canonical_json(
                {
                    k: v
                    for k, v in rc_bundle.items()
                    if k != "RELEASE_CANDIDATE_BUNDLE_SHA256"
                }
            )
        )
        write_private(PRIVATE_EXEC / "RELEASE_CANDIDATE_POINTER.json", rc_pointer)
        write_private(PRIVATE_EXEC / "RELEASE_CANDIDATE_BUNDLE.json", rc_bundle)
        write_repo(REPO_ART / "release_candidate_pointer.json", rc_pointer)
        write_repo(
            REPO_ART / "release_candidate_bundle.json",
            {
                k: v
                for k, v in rc_bundle.items()
                if k
                not in {
                    # keep public
                }
            },
        )

    receipt = {
        "PHASE_RULE": EXECUTE_PHASE,
        "EXPERIMENT_ID": EXECUTE_EXPERIMENT_ID,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "RESULT_ID": RESULT_ID,
        "QUALIFICATION_DISPOSITION": decision["QUALIFICATION_DISPOSITION"],
        "RELEASE_OUTCOME": decision["RELEASE_OUTCOME"],
        "RELEASE_ELIGIBLE": release_eligible,
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "failure_class": failure_class,
        "PACKAGE_ID": CORE_PACKAGE_ID,
        "PACKAGE_SHA256": EXPECTED_PACKAGE_SHA256,
        "qual_seal_sha256": expected_seal,
        "n_rows": len(rows),
        "qualification_model_executions": 1,
        "evaluation_spent": True,
        "QUALIFICATION_STATE": "EVALUATION_SPENT",
        "cold_load_ok": cold_load_ok,
        "round_trip_ok": round_trip_ok,
        "encoder_trainable": n_train,
        "encoder_state_hash": enc_hash,
        "metrics": metrics,
        "gate_eval": gate_eval,
        "retention": retention,
        "CORE_QUALIFICATION_GATES": dict(CORE_QUALIFICATION_GATES),
        "function_advisory": {
            "role": "ADVISORY_ONLY",
            "blocking": False,
            "macro_f1": metrics["FUNCTION_advisory_macro_f1"],
            "micro_f1": metrics["FUNCTION_advisory_micro_f1"],
        },
        "runtime_contract": runtime_contract(),
        "limitations": limitations(),
        "RELEASE_CANDIDATE_POINTER": rc_pointer,
        "HUB_PUBLISH_AUTHORIZED": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "code_revision": code_revision(),
        "sealed_at": sealed_at,
    }
    receipt["SYSTEM_CORE_QUALIFICATION_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in receipt.items()
                if k != "SYSTEM_CORE_QUALIFICATION_RECEIPT_SHA256"
            }
        )
    )

    summary = {
        "QUALIFICATION_DISPOSITION": decision["QUALIFICATION_DISPOSITION"],
        "RELEASE_OUTCOME": decision["RELEASE_OUTCOME"],
        "RELEASE_ELIGIBLE": release_eligible,
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "failure_class": failure_class,
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "n_rows": len(rows),
        "PACKAGE_SHA256": EXPECTED_PACKAGE_SHA256,
        "qual_seal_sha256": expected_seal,
        "qualification_model_executions": 1,
        "evaluation_spent": True,
        "core_system_macro_f1": metrics["core_system_macro_f1"],
        "DOMAIN_macro_f1": metrics["DOMAIN_macro_f1"],
        "DOMAIN_micro_f1": metrics["DOMAIN_micro_f1"],
        "MEDIATION_macro_f1": metrics["MEDIATION_macro_f1"],
        "MEDIATION_micro_f1": metrics["MEDIATION_micro_f1"],
        "zero_label_false_positive_rate": metrics["zero_label_false_positive_rate"],
        "zero_label_exact_rejection": metrics["zero_label_exact_rejection"],
        "mean_predicted_labels_on_zero_gold": metrics[
            "mean_predicted_labels_on_zero_gold"
        ],
        "sample_f1": metrics["sample_f1"],
        "jaccard": metrics["jaccard"],
        "raw_hierarchy_violation_rate": metrics["raw_hierarchy_violation_rate"],
        "hierarchy_violation_rate": metrics["hierarchy_violation_rate"],
        "FUNCTION_advisory_macro_f1": metrics["FUNCTION_advisory_macro_f1"],
        "gate_pass": gate_eval["pass"],
        "gates": {k: v["pass"] for k, v in gate_eval["gates"].items()},
        "retention_band": retention["band"],
        "retention_ratio": retention["relative_retention"],
        "absolute_degradation": retention["absolute_degradation"],
        "cold_load_ok": cold_load_ok,
        "round_trip_ok": round_trip_ok,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RECEIPT": receipt["SYSTEM_CORE_QUALIFICATION_RECEIPT_SHA256"],
        "RELEASE_CANDIDATE_POINTER": RELEASE_CANDIDATE_POINTER
        if release_eligible
        else None,
    }

    write_private(PRIVATE_EXEC / "METRICS.json", metrics)
    write_private(PRIVATE_EXEC / "GATE_EVAL.json", gate_eval)
    write_private(PRIVATE_EXEC / "RETENTION.json", retention)
    write_private(PRIVATE_EXEC / "RECEIPT.json", receipt)
    write_private(PRIVATE_EXEC / "SUMMARY.json", summary)
    write_repo(REPO_ART / "metrics.json", metrics)
    write_repo(REPO_ART / "gate_eval.json", gate_eval)
    write_repo(REPO_ART / "retention.json", retention)
    write_repo(REPO_ART / "receipt.json", receipt)
    write_repo(REPO_ART / "RECEIPT.json", receipt)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(REPO_ART / "summary.json", summary)
    write_repo(
        SPEC / "classification-v6-core-qualification-execute-receipt-20261002.json",
        receipt,
    )

    md = f"""# EXECUTE_V6_CORE_QUALIFICATION_ONCE

```text
QUALIFICATION_DISPOSITION = {decision['QUALIFICATION_DISPOSITION']}
RELEASE_OUTCOME           = {decision['RELEASE_OUTCOME']}
RELEASE_ELIGIBLE          = {release_eligible}
NEXT_ACTION               = {decision['NEXT_ACTION']}
failure_class             = {failure_class}

QUALIFICATION_ID = {QUALIFICATION_ID}
n_rows           = {len(rows)}
PACKAGE_SHA256   = {EXPECTED_PACKAGE_SHA256}
seal             = {expected_seal}
model_executions = 1
evaluation_spent = true

core system macro-F1 = {metrics['core_system_macro_f1']:.4f}
DOMAIN   macro/micro = {metrics['DOMAIN_macro_f1']:.4f} / {metrics['DOMAIN_micro_f1']:.4f}
MEDIATION macro/micro = {metrics['MEDIATION_macro_f1']:.4f} / {metrics['MEDIATION_micro_f1']:.4f}
zero-FP / exact      = {metrics['zero_label_false_positive_rate']:.4f} / {metrics['zero_label_exact_rejection']:.4f}
mean pred on zero    = {metrics['mean_predicted_labels_on_zero_gold']:.4f}
sample-F1 / Jaccard  = {metrics['sample_f1']:.4f} / {metrics['jaccard']:.4f}
hierarchy raw/post   = {metrics['raw_hierarchy_violation_rate']:.6f} / {metrics['hierarchy_violation_rate']:.6f}
FUNCTION advisory    = {metrics['FUNCTION_advisory_macro_f1']:.4f} (NON_BLOCKING)

REP_V3→QUAL retention = {retention['band']} ({retention['relative_retention']:.3f})
absolute_degradation  = {retention['absolute_degradation']:.4f}

gate_pass = {gate_eval['pass']}
HUB_PUBLISH_AUTHORIZED = false
```

Frozen gates unchanged after results. QUAL-002/003 unreused.
"""
    write_repo(SPEC / "classification-v6-core-qualification-execute-20261002.md", md)
    write_private(PRIVATE_EXEC / "SETTLEMENT.md", md)
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0 if execution_ok else 4


def main() -> int:
    if os.environ.get("HLX_V6_CORE_QUAL_EXEC_INNER") == "1":
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
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow:/home/morpheus/Hyperlex/scripts/spark",
        "-e",
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        "HLX_V6_CORE_QUAL_EXEC_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v6_core_qualification_execute.py"),
    ]
    log = PRIVATE_EXEC / "execute_console.log"
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
