"""WIRE_V5_STAGE_B_RETRIEVAL_ON_STAGE_A_BEST — validate Stage-B behind STAGE_A_BEST.

Builds a fresh exemplar index from V1R9 train POSITIVE_EVIDENCE using the
promoted two-stage Stage-A encoder stack. Calibrates Stage-B floors on
validation. Does not create/score a reserve and does not mutate BEST or
STAGE_A_BEST.
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
    "classification-v5-stage-a-negative-evidence-surface-v1r9-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a"
STAGE_A_BEST_DIR = Path("/home/morpheus/.hyperlex/models/STAGE_A_BEST")
STAGE_A_BEST_WEIGHTS = STAGE_A_BEST_DIR / "model.safetensors"
STAGE_A_BEST_SHA = "cd2829c1b5fb823fc03f18efe66a7387124ef44be2545b9e385a17eb6237bf5c"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
BEST_PATH_FILE = Path("/home/morpheus/.hyperlex/models/BEST.path")
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
PRIVATE = Path("/home/morpheus/hlx-private/classification-v5-stage-b-20260930")
DEST = PRIVATE / "STAGE_B_VALIDATION.json"
INDEX_DEST = PRIVATE / "STAGE_B_INDEX.json"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ARTIFACTS = (
    REPO / "artifacts" / "experiments" / "HLX-CLASSIFICATION-V5-STAGE-B-001"
)
SPEC_DIR = REPO / "specs" / "007-hyperlexical-model"

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


def sudo_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except PermissionError:
        completed = subprocess.run(
            ["sudo", "-n", "cat", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


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
    override = (os.environ.get("HLX_V5_STAGE_B_CODE_REVISION") or "").strip()
    if override:
        return override
    try:
        completed = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def pin_inputs() -> None:
    if not DATASET.exists():
        fail(f"missing_dataset:{DATASET}")
    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset_digest_mismatch")
    if not STAGE_A_BEST_WEIGHTS.exists():
        fail("STAGE_A_BEST_missing")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_sha_mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_sha_mismatch")
    expected_best_path = str(
        Path(
            "/home/morpheus/.hyperlex/models/"
            "hyperlex-encoder-modernbert-base-seed-select004"
        )
    )
    if BEST_PATH_FILE.read_text(encoding="utf-8").strip() != expected_best_path:
        fail("BEST_path_mutated")


def inner() -> int:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file

    from hyperlexical.classification_v5_stage_a_two_stage import (
        gate1_probabilities,
        gate2_probabilities,
    )
    from hyperlexical.classification_v5_stage_a_two_stage_promote import (
        decide_canonical_stage_a,
    )
    from hyperlexical.classification_v5_stage_b import (
        STAGE_A_BEST_SHA256,
        assemble_stage_b_receipt,
        build_stage_b_index,
        calibrate_stage_b_thresholds,
        evaluate_end_to_end,
        gold_end_to_end,
        is_index_positive_row,
        next_action_for_stage_b,
        reserve_authorization,
        retrieval_candidates_from_embedding,
        stage_b_contract,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.holdout_guard import normalized_text_sha256
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    pin_inputs()
    if PRIVATE.exists() and (PRIVATE / "STAGE_B_VALIDATION.json").exists():
        fail(f"output_already_exists:{PRIVATE}")
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)

    rows = load_jsonl(DATASET)
    train_rows = [r for r in rows if r.get("split") == "train"]
    val_rows = [r for r in rows if r.get("split") == "validation"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("Stage B validation requires CUDA")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    gate1_head = nn.Linear(HIDDEN, 2)
    gate2_head = nn.Linear(HIDDEN, 2)

    best_split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    if apply_encoder_trainable(encoder, best_split.get("encoder") or {})["loaded"] != 48:
        fail("BEST_encoder_overlay_incomplete")
    stage_a_tensors = load_file(str(STAGE_A_BEST_WEIGHTS), device="cpu")
    if any(k.startswith("evidence_head.") for k in stage_a_tensors):
        fail("flat_evidence_head_in_STAGE_A_BEST")
    stage_a_split = split_weight_tensors(stage_a_tensors)
    loaded_a = apply_encoder_trainable(encoder, stage_a_split.get("encoder") or {})
    if loaded_a["loaded"] != 12:
        fail(f"STAGE_A_BEST_overlay_incomplete:{loaded_a['loaded']}")
    freeze_encoder(encoder, last_trainable=2)
    with torch.no_grad():
        gate1_head.weight.copy_(stage_a_split["gate1_head"]["weight"])
        gate1_head.bias.copy_(stage_a_split["gate1_head"]["bias"])
        gate2_head.weight.copy_(stage_a_split["gate2_head"]["weight"])
        gate2_head.bias.copy_(stage_a_split["gate2_head"]["bias"])

    encoder.to(device).eval()
    gate1_head.to(device).eval()
    gate2_head.to(device).eval()

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
                pooled = torch.nn.functional.normalize(pooled, dim=-1)
                vectors.extend(pooled.detach().cpu().tolist())
        return vectors

    index_rows = [row for row in train_rows if is_index_positive_row(row)]
    if len(index_rows) < 100:
        fail(f"index_positives_too_few:{len(index_rows)}")
    identity_text = {}
    for row in index_rows:
        identity = normalized_text_sha256(str(row["text"]))
        identity_text.setdefault(identity, str(row["text"]))
    identities = sorted(identity_text)
    vectors = embed_texts([identity_text[i] for i in identities])
    embeddings = {identity: vector for identity, vector in zip(identities, vectors)}
    index = build_stage_b_index(train_rows, embeddings)
    write_private(INDEX_DEST, index)

    score_rows = []
    with torch.no_grad():
        for row in val_rows:
            text = str(row["text"])
            encoded = tokenizer(
                [text],
                padding=True,
                truncation=True,
                max_length=int(MAX_LEN),
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            g1 = gate1_probabilities(gate1_head(pooled)[0].detach().cpu().tolist())
            g2 = gate2_probabilities(gate2_head(pooled)[0].detach().cpu().tolist())
            evidence_decision = decide_canonical_stage_a(
                p_possible=float(g1["POSSIBLE_EVIDENCE"]),
                p_confirmed=float(g2["CONFIRMED_PRESENT"]),
            )
            hidden = torch.nn.functional.normalize(pooled, dim=-1)[0].detach().cpu().tolist()
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
                    "evidence_decision": evidence_decision,
                    "evidence_label": row["evidence_label"],
                    "evidence_subtype": row["evidence_subtype"],
                    "gold_decision_type": gold["decision_type"],
                    "gold_family": gold["family"],
                    "identity": row["identity"],
                    "p_confirmed": float(g2["CONFIRMED_PRESENT"]),
                    "p_possible": float(g1["POSSIBLE_EVIDENCE"]),
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

    authorization = reserve_authorization(metrics)
    next_action = next_action_for_stage_b(authorization)
    receipt = assemble_stage_b_receipt(
        {
            "authorization": authorization,
            "best_sha256": BEST_SHA,
            "calibration": calibration,
            "index_sha256": index["index_sha256"],
            "metrics": metrics,
            "next_action": next_action,
        }
    )
    receipt["code_revision"] = code_revision()
    # Re-hash after adding code_revision.
    bare = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text

    receipt["receipt_sha256"] = sha256_text(canonical_json(bare))

    write_private(DEST, receipt)
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
        "EXPERIMENT_ID": "HLX-CLASSIFICATION-V5-STAGE-B-001",
        "MODEL_WIDE_BEST": BEST_SHA,
        "RESERVE_CONSUMED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "TRAIN": False,
        "authorization": authorization["decision"],
        "false_evidence_entry_rate_on_none": metrics[
            "false_evidence_entry_rate_on_none"
        ],
        "family_emission_coverage": metrics.get("family_emission_coverage"),
        "family_emission_precision": metrics.get("family_emission_precision"),
        "feasible": calibration.get("feasible"),
        "index_sha256": index["index_sha256"],
        "next_action": next_action,
        "primary_gate_pass": metrics["primary_gate_pass"],
        "receipt_sha256": receipt["receipt_sha256"],
        "secondary_gate_pass": metrics["secondary_gate_pass"],
        "selective_accuracy": metrics.get("selective_accuracy"),
        "thresholds": {
            "gate1_threshold": 0.75,
            "gate2_threshold": 0.50,
            "minimum_family_score": calibration.get("minimum_family_score"),
            "minimum_top1_top2_margin": calibration.get("minimum_top1_top2_margin"),
        },
    }
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_repo(REPO_ARTIFACTS / "stage_b_validation_receipt.json", receipt)
    write_repo(REPO_ARTIFACTS / "stage_b_validation_summary.json", summary)
    write_repo(REPO_ARTIFACTS / "stage_b_contract.json", stage_b_contract())
    write_repo(
        SPEC_DIR / "classification-v5-stage-b-validation-receipt-20260930.json",
        receipt,
    )

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_during_stage_b")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_mutated_during_stage_b")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V5_STAGE_B_INNER") == "1" or "--inner" in sys.argv:
        return inner()

    from hyperlexical.classification_v5_stage_b import stage_b_contract, WIRE_ACTION

    pin_inputs()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(
        PRIVATE / "LAUNCH.json",
        {
            "authorization": WIRE_ACTION,
            "best_sha256": BEST_SHA,
            "contract": stage_b_contract(),
            "dataset_sha256": DATASET_SHA,
            "moves_best": False,
            "stage_a_best_sha256": STAGE_A_BEST_SHA,
            "train": False,
            "v5_reserve": None,
        },
    )
    revision = code_revision()
    command = [
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
        "HLX_V5_STAGE_B_INNER=1",
        "-e",
        f"HLX_V5_STAGE_B_CODE_REVISION={revision}",
        "-e",
        "HF_HUB_OFFLINE=1",
        "-e",
        "TRANSFORMERS_OFFLINE=1",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v5_stage_b_validation.py"),
    ]
    log_path = PRIVATE / "stage_b_validation.log"
    print(json.dumps({"launch": command[-1], "log": str(log_path)}, sort_keys=True), flush=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(
            command, check=False, stdout=handle, stderr=subprocess.STDOUT
        )
    try:
        print(log_path.read_text(encoding="utf-8")[-12000:])
    except OSError:
        pass
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_after_stage_b")
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
