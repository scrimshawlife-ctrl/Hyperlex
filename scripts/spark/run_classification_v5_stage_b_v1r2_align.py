"""ALIGN_V5_STAGE_B_TO_V1R2 — build/eval Stage-B on V1R2 under canonical Stage-A.

Rebuilds Stage-B index on V1R2 with factorized STAGE_A_BEST embeddings and
calibrates floors on V1R2 validation. Does not retrain Stage-A, score spent
reserve, or mutate MODEL_WIDE_BEST. Historical V1R9 index retained.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-identifiability-filtered-v1r2-20261001"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "492ed36751c7fdc40fe10bcdfabb69fa8783f8680259c31b3a64ee6903326d73"
SURFACE_ID = "HYPERLEX_V5_STAGE_A_IDENTIFIABILITY_FILTERED_SURFACE_V1R2"
STAGE_A_BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/STAGE_A_BEST/model.safetensors"
)
STAGE_A_BEST_SHA = (
    "f2b00c5dfeb087288fc1686c901fbc8b52a8ba7a7b51cb83ff038656f93617fa"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-b-v1r2-20261001"
)
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ART = (
    REPO / "artifacts" / "experiments" / "HLX-CLASSIFICATION-V5-STAGE-B-V1R2-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"

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
        return subprocess.run(
            ["sudo", "-n", "sha256sum", str(path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split()[0]


def write_private(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    os.chmod(path, 0o600)


def write_repo(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
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


def code_revision() -> str:
    override = (os.environ.get("HLX_V5_STAGE_A_CODE_REVISION") or "").strip()
    if override:
        return override
    try:
        return subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(2)


def inner() -> int:
    import torch
    import torch.nn.functional as F
    from torch import nn
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v5_stage_a_canonical import (
        decide_canonical_stage_a,
        may_invoke_stage_b,
        verify_canonical_checkpoint_keys,
        utc_now_iso,
    )
    from hyperlexical.classification_v5_stage_b import (
        build_stage_b_index,
        calibrate_stage_b_thresholds,
        evaluate_end_to_end,
        gold_end_to_end,
        is_index_positive_row,
        retrieval_candidates_from_embedding,
    )
    from hyperlexical.classification_v5_stage_b_v1r2_align import (
        active_stage_b_v1r2_contract,
        alignment_contract,
        build_alignment_receipt,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.holdout_guard import normalized_text_sha256
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    if sha256_file(DATASET) != DATASET_SHA:
        fail("v1r2_dataset_digest_mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mismatch")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mismatch")

    tensors = load_file(str(STAGE_A_BEST_WEIGHTS), device="cpu")
    keys_ok = verify_canonical_checkpoint_keys(list(tensors.keys()))
    if not keys_ok["pass"]:
        fail(f"checkpoint_incomplete:{json.dumps(keys_ok, sort_keys=True)}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("v1r2 stage-b align requires CUDA")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    relation_head = nn.Linear(HIDDEN, 2)
    resolvability_head = nn.Linear(HIDDEN, 2)

    best_split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    if apply_encoder_trainable(encoder, best_split.get("encoder") or {})["loaded"] != 48:
        fail("BEST_encoder_overlay_incomplete")
    split = split_weight_tensors(tensors)
    loaded = apply_encoder_trainable(encoder, split.get("encoder") or {})
    if loaded["loaded"] != 12:
        fail(f"STAGE_A_overlay_incomplete:{loaded['loaded']}")
    freeze_encoder(encoder, last_trainable=2)
    with torch.no_grad():
        relation_head.weight.copy_(split["relation_head"]["weight"])
        relation_head.bias.copy_(split["relation_head"]["bias"])
        resolvability_head.weight.copy_(split["resolvability_head"]["weight"])
        resolvability_head.bias.copy_(split["resolvability_head"]["bias"])

    encoder.to(device).eval()
    relation_head.to(device).eval()
    resolvability_head.to(device).eval()

    def embed_texts(texts: list[str]) -> list[list[float]]:
        vectors = []
        with torch.no_grad():
            for start in range(0, len(texts), 32):
                batch = texts[start : start + 32]
                encoded = tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=int(MAX_LEN),
                    return_tensors="pt",
                )
                encoded = {k: v.to(device) for k, v in encoded.items()}
                pooled = encoder(**encoded).last_hidden_state[:, 0]
                pooled = F.normalize(pooled, dim=-1)
                vectors.extend(pooled.detach().cpu().tolist())
        return vectors

    rows = load_jsonl(DATASET)
    train_rows = [r for r in rows if r.get("split") == "train"]
    val_rows = [r for r in rows if r.get("split") == "validation"]
    index_rows = [r for r in train_rows if is_index_positive_row(r)]
    if len(index_rows) < 100:
        fail(f"index_positives_too_few:{len(index_rows)}")

    identity_text = {}
    for row in index_rows:
        identity = normalized_text_sha256(str(row["text"]))
        identity_text.setdefault(identity, str(row["text"]))
    identities = sorted(identity_text)
    vectors = embed_texts([identity_text[i] for i in identities])
    embeddings = {identity: vector for identity, vector in zip(identities, vectors)}
    index = build_stage_b_index(
        train_rows,
        embeddings,
        surface_rule=SURFACE_ID,
        surface_dataset_sha256=DATASET_SHA,
    )
    write_private(PRIVATE / "STAGE_B_INDEX.json", index)

    score_rows = []
    with torch.no_grad():
        for row in val_rows:
            encoded = tokenizer(
                [str(row["text"])],
                padding=True,
                truncation=True,
                max_length=int(MAX_LEN),
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            rel = F.softmax(relation_head(pooled)[0], dim=-1).tolist()
            res = F.softmax(resolvability_head(pooled)[0], dim=-1).tolist()
            decision = decide_canonical_stage_a(
                p_relation=float(rel[1]), p_resolvable=float(res[1])
            )
            hidden = F.normalize(pooled, dim=-1)[0].detach().cpu().tolist()
            ranked = retrieval_candidates_from_embedding(
                hidden,
                index["records"],
                family_vocabulary=index.get("family_vocabulary"),
            )
            gold = gold_end_to_end(row)
            candidates = ranked["candidates"]
            top3 = candidates[2] if len(candidates) > 2 else None
            score_rows.append(
                {
                    "evidence_decision": decision,
                    "evidence_label": row["evidence_label"],
                    "evidence_subtype": row["evidence_subtype"],
                    "gold_decision_type": gold["decision_type"],
                    "gold_family": gold["family"],
                    "identity": row["identity"],
                    "invoked_stage_b": may_invoke_stage_b(decision),
                    "p_relation": float(rel[1]),
                    "p_resolvable": float(res[1]),
                    "top1_family": ranked["top1"]["family"],
                    "top1_score": ranked["top1"]["score"],
                    "top2_family": ranked["top2"]["family"],
                    "top2_score": ranked["top2"]["score"],
                    "top3_family": None if top3 is None else top3["family"],
                    "top3_score": None if top3 is None else top3["score"],
                }
            )

    calibration = calibrate_stage_b_thresholds(score_rows)
    if calibration.get("feasible"):
        metrics = evaluate_end_to_end(
            score_rows,
            family_score_min=float(calibration["minimum_family_score"]),
            family_margin_min=float(calibration["minimum_top1_top2_margin"]),
        )
    else:
        fallback = calibration.get("fallback") or {}
        score_min = float(fallback.get("minimum_family_score") or 0.0)
        margin_min = float(fallback.get("minimum_top1_top2_margin") or 0.0)
        metrics = evaluate_end_to_end(
            score_rows,
            family_score_min=score_min,
            family_margin_min=margin_min,
        )
        metrics["calibration_feasible"] = False
    metrics["false_evidence_entry_rate_on_none"] = calibration[
        "false_evidence_entry_rate_on_none"
    ]
    metrics["primary_gate_pass"] = calibration["primary_gate_pass"]
    metrics["secondary_gate_pass"] = bool(
        metrics["primary_gate_pass"]
        and metrics.get("family_emission_precision") is not None
        and float(metrics["family_emission_precision"]) + 1e-12 >= 0.80
    )

    # Entry gating integrity on scored rows.
    none_entered = sum(
        1
        for r in score_rows
        if r["evidence_decision"] == "NO_EVIDENCE" and r["invoked_stage_b"]
    )
    uncertain_entered = sum(
        1
        for r in score_rows
        if r["evidence_decision"] == "UNCERTAIN" and r["invoked_stage_b"]
    )
    metrics["gating"] = {
        "none_entered_stage_b": none_entered,
        "uncertain_entered_stage_b": uncertain_entered,
        "pass": none_entered == 0 and uncertain_entered == 0,
    }
    if not metrics["gating"]["pass"]:
        metrics["primary_gate_pass"] = False
        metrics["secondary_gate_pass"] = False

    revision = code_revision()
    aligned_at = utc_now_iso()
    receipt = build_alignment_receipt(
        metrics=metrics,
        calibration=calibration,
        index_sha256=index["index_sha256"],
        code_revision=revision,
        n_index_records=len(index["records"]),
        n_validation=len(score_rows),
        aligned_at=aligned_at,
    )

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(PRIVATE / "STAGE_B_V1R2_ALIGNMENT.json", receipt)
    write_private(PRIVATE / "CALIBRATION.json", calibration)
    write_private(
        PRIVATE / "SCORE_ROWS_META.json",
        {
            "n": len(score_rows),
            "n_evidence_present": sum(
                1 for r in score_rows if r["evidence_decision"] == "EVIDENCE_PRESENT"
            ),
            "n_no_evidence": sum(
                1 for r in score_rows if r["evidence_decision"] == "NO_EVIDENCE"
            ),
            "n_uncertain": sum(
                1 for r in score_rows if r["evidence_decision"] == "UNCERTAIN"
            ),
        },
    )

    summary = {
        "BEST_MUTATED": False,
        "EXPERIMENT_ID": "HLX-CLASSIFICATION-V5-STAGE-B-V1R2-001",
        "MODEL_WIDE_BEST": BEST_SHA,
        "NEXT_ACTION": receipt["NEXT_ACTION"],
        "RESERVE_CONSUMED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA,
        "STAGE_B_V1R2_ALIGNMENT": receipt["state"]["STAGE_B_V1R2_ALIGNMENT"],
        "STAGE_B_V1R2_ALIGNMENT_RECEIPT_SHA256": receipt[
            "STAGE_B_V1R2_ALIGNMENT_RECEIPT_SHA256"
        ],
        "TRAIN": False,
        "false_evidence_entry_rate_on_none": metrics[
            "false_evidence_entry_rate_on_none"
        ],
        "family_emission_coverage": metrics.get("family_emission_coverage"),
        "family_emission_precision": metrics.get("family_emission_precision"),
        "feasible": calibration.get("feasible"),
        "gating_pass": metrics["gating"]["pass"],
        "index_sha256": index["index_sha256"],
        "n_index_records": len(index["records"]),
        "n_validation": len(score_rows),
        "primary_gate_pass": metrics["primary_gate_pass"],
        "secondary_gate_pass": metrics["secondary_gate_pass"],
        "selective_accuracy": metrics.get("selective_accuracy"),
        "thresholds": {
            "relation_threshold": 0.60,
            "resolvability_threshold": 0.75,
            "minimum_family_score": calibration.get("minimum_family_score"),
            "minimum_top1_top2_margin": calibration.get("minimum_top1_top2_margin"),
        },
    }
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_repo(REPO_ART / "stage_b_v1r2_alignment_receipt.json", receipt)
    write_repo(REPO_ART / "stage_b_v1r2_alignment_summary.json", summary)
    write_repo(REPO_ART / "alignment_contract.json", alignment_contract())
    write_repo(
        SPEC / "classification-v5-stage-b-v1r2-alignment-receipt-20261001.json",
        receipt,
    )

    if receipt["state"]["applied"]:
        active = active_stage_b_v1r2_contract(
            index_sha256=index["index_sha256"],
            minimum_family_score=float(calibration["minimum_family_score"]),
            minimum_top1_top2_margin=float(calibration["minimum_top1_top2_margin"]),
        )
        write_private(PRIVATE / "STAGE_B_ACTIVE_CONTRACT.json", active)
        write_repo(REPO_ART / "stage_b_v1r2_active_contract.json", active)
        write_repo(
            SPEC / "classification-v5-stage-b-v1r2-active-contract-20261001.json",
            active,
        )

    write_repo(
        SPEC / "classification-v5-stage-b-v1r2-align-20261001.md",
        f"""# ALIGN_V5_STAGE_B_TO_V1R2

```text
STAGE_B_V1R2_ALIGNMENT = {summary['STAGE_B_V1R2_ALIGNMENT']}
STAGE_A_BEST = {STAGE_A_BEST_SHA}
surface = {SURFACE_ID}
index_sha256 = {index['index_sha256']}
n_index_records = {len(index['records'])}
n_validation = {len(score_rows)}
false_entry = {metrics['false_evidence_entry_rate_on_none']}
family_precision = {metrics.get('family_emission_precision')}
floors = {calibration.get('minimum_family_score')} / {calibration.get('minimum_top1_top2_margin')}
gating_pass = {metrics['gating']['pass']}
RECEIPT = {receipt['STAGE_B_V1R2_ALIGNMENT_RECEIPT_SHA256']}
NEXT_ACTION = {receipt['NEXT_ACTION']}
```

Historical V1R9 index retained. Reserve not scored. Stage-A not retrained.
""",
    )

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mutated")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if receipt["state"]["applied"] else 2


def main() -> int:
    if os.environ.get("HLX_V5_STAGE_B_V1R2_INNER") == "1":
        return inner()

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    revision = code_revision()
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
        "HLX_V5_STAGE_B_V1R2_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v5_stage_b_v1r2_align.py"),
    ]
    log = PRIVATE / "align_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(
            cmd, check=False, stdout=handle, stderr=subprocess.STDOUT
        )
    try:
        print(log.read_text(encoding="utf-8")[-12000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
