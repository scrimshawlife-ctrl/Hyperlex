"""REVIEW_V5_STAGE_A_TWO_STAGE_PROMOTION — read-only cold-load + integrity review.

Does not train, score reserve, alter thresholds, or move BEST.
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
AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-two-stage-train-v1-20260930"
)
RUN_ROOT = AUTH_DEST / "classification-v5-stage-a-two-stage-001"
SELECTED = RUN_ROOT / "selected" / "model.safetensors"
AUTH_FILE = AUTH_DEST / "AUTHORIZATION.json"
RESOLVED = AUTH_DEST / "RESOLVED_TRAINING_CONFIG.json"
WEIGHTS = AUTH_DEST / "TWO_STAGE_CLASS_WEIGHTS.json"
WITNESS = RUN_ROOT / "TWO_STAGE_SPLIT_WITNESS.json"
RECEIPT = RUN_ROOT / "RUN_RECEIPT.json"
SELECTED_MANIFEST = RUN_ROOT / "SELECTED_CHECKPOINT.json"
THRESHOLD_GRID = RUN_ROOT / "diagnostics" / "threshold_grid.json"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REVIEW_DEST = AUTH_DEST / "promotion_review"
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001"
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


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
        completed = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        head = REPO / ".git" / "HEAD"
        if head.is_file():
            text = head.read_text(encoding="utf-8").strip()
            if text.startswith("ref:"):
                ref = text.split(":", 1)[1].strip()
                ref_path = REPO / ".git" / ref
                if ref_path.is_file():
                    return ref_path.read_text(encoding="utf-8").strip()
            elif len(text) >= 40:
                return text[:40]
        return "UNKNOWN"


def cold_load_replay() -> dict:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file

    from hyperlexical.classification_v5_stage_a_two_stage import (
        gate1_probabilities,
        gate2_probabilities,
    )
    from hyperlexical.classification_v5_stage_a_two_stage_promotion_review import (
        EXPECTED_GATE1_THRESHOLD as G1,
        EXPECTED_GATE2_PRESENT_THRESHOLD as G2,
        EXPECTED_SELECTED_CHECKPOINT_SHA256,
        replay_decisions,
        verify_architecture_identity,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    # Pin names from promotion review module (thresholds frozen).
    assert G1 == 0.75 and G2 == 0.50

    ckpt_sha = sha256_file(SELECTED)
    if ckpt_sha != EXPECTED_SELECTED_CHECKPOINT_SHA256:
        fail(f"selected_checkpoint_sha_mismatch:{ckpt_sha}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("promotion review cold-load requires CUDA")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    gate1_head = nn.Linear(HIDDEN, 2)
    gate2_head = nn.Linear(HIDDEN, 2)

    tensors = load_file(str(SELECTED), device="cpu")
    arch = verify_architecture_identity(list(tensors.keys()))
    if not arch["pass"]:
        fail(f"architecture_identity_fail:{json.dumps(arch['checks'], sort_keys=True)}")

    split = split_weight_tensors(tensors)
    loaded = apply_encoder_trainable(encoder, split.get("encoder") or {})
    if loaded["loaded"] != 12:
        fail(f"encoder_overlay_incomplete:{loaded['loaded']}")
    # Ensure earlier layers remain frozen structurally for inference; freeze call
    # matches train contract (last 2 trainable) without mutating BEST.
    freeze_encoder(encoder, last_trainable=2)
    with torch.no_grad():
        gate1_head.weight.copy_(split["gate1_head"]["weight"])
        gate1_head.bias.copy_(split["gate1_head"]["bias"])
        gate2_head.weight.copy_(split["gate2_head"]["weight"])
        gate2_head.bias.copy_(split["gate2_head"]["bias"])

    encoder.to(device)
    gate1_head.to(device)
    gate2_head.to(device)
    encoder.eval()
    gate1_head.eval()
    gate2_head.eval()

    rows = [r for r in load_jsonl(DATASET) if r.get("split") == "validation"]
    golds, p_possible, p_confirmed = [], [], []
    max_len = int(MAX_LEN)
    with torch.no_grad():
        for row in rows:
            encoded = tokenizer(
                [str(row["text"])],
                padding=True,
                truncation=True,
                max_length=max_len,
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            g1 = gate1_probabilities(gate1_head(pooled)[0].detach().cpu().tolist())
            g2 = gate2_probabilities(gate2_head(pooled)[0].detach().cpu().tolist())
            golds.append(str(row["evidence_label"]))
            p_possible.append(float(g1["POSSIBLE_EVIDENCE"]))
            p_confirmed.append(float(g2["CONFIRMED_PRESENT"]))

    replay = replay_decisions(
        golds=golds,
        p_possible=p_possible,
        p_confirmed=p_confirmed,
        gate1_threshold=0.75,
        gate2_present_threshold=0.50,
    )
    replay["architecture_identity"] = arch
    replay["n_validation"] = len(rows)
    replay["selected_checkpoint_sha256"] = ckpt_sha
    replay["cold_load"] = True
    return replay


def inner() -> int:
    from hyperlexical.classification_v5_stage_a_two_stage_promotion_review import (
        EXPECTED_SELECTED_CHECKPOINT_SHA256,
        build_promotion_review_receipt,
        verify_settlement_integrity,
        verify_threshold_selection_rule,
    )

    for path in (
        AUTH_FILE,
        RESOLVED,
        WEIGHTS,
        WITNESS,
        RECEIPT,
        SELECTED_MANIFEST,
        THRESHOLD_GRID,
        SELECTED,
        DATASET,
    ):
        if not path.exists():
            fail(f"missing_required_artifact:{path}")

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset_digest_mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_during_review")

    auth = load_json(AUTH_FILE)
    resolved = load_json(RESOLVED)
    weights = load_json(WEIGHTS)
    witness = load_json(WITNESS)
    receipt = load_json(RECEIPT)
    selected_manifest = load_json(SELECTED_MANIFEST)
    threshold_grid = load_json(THRESHOLD_GRID)
    selected_sha = sha256_file(SELECTED)

    integrity = verify_settlement_integrity(
        auth=auth,
        resolved=resolved,
        weights=weights,
        witness=witness,
        receipt=receipt,
        selected_manifest=selected_manifest,
        threshold_grid=threshold_grid,
        selected_checkpoint_sha256=selected_sha,
    )
    if not integrity["pass"]:
        # Still seal an INVALID review; do not cold-load if integrity fails hard.
        review = build_promotion_review_receipt(
            integrity=integrity,
            architecture={"pass": False, "checks": {}, "note": "skipped"},
            replay={"pass": False, "note": "skipped_due_to_invalid_settlement"},
            threshold_rule={"pass": False},
            code_revision=code_revision(),
        )
        REVIEW_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
        write_private(REVIEW_DEST / "PROMOTION_REVIEW.json", review)
        write_repo(REPO_ARTIFACTS / "promotion_review_receipt.json", review)
        print(json.dumps(review, indent=2, sort_keys=True))
        return 2

    thr_rule = verify_threshold_selection_rule(
        threshold_grid=threshold_grid, receipt=receipt
    )
    replay = cold_load_replay()
    architecture = replay.pop("architecture_identity")

    # Persist replay artifact for hash retention.
    REVIEW_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    replay_artifact = {
        "SELECTED_CHECKPOINT_SHA256": EXPECTED_SELECTED_CHECKPOINT_SHA256,
        "cold_load": True,
        "metrics": replay["metrics"],
        "n_validation": replay["n_validation"],
        "parity": replay["parity"],
        "pass": replay["pass"],
        "replay_hash": replay["replay_hash"],
        "schema": "hyperlex.classification.v5.stage_a_two_stage_promotion_replay.v1",
        "thresholds_match": replay["thresholds_match"],
    }
    write_private(REVIEW_DEST / "VALIDATION_REPLAY.json", replay_artifact)
    write_private(RUN_ROOT / "diagnostics" / "promotion_validation_replay.json", replay_artifact)

    review = build_promotion_review_receipt(
        integrity=integrity,
        architecture=architecture,
        replay=replay_artifact,
        threshold_rule=thr_rule,
        code_revision=code_revision(),
    )
    write_private(REVIEW_DEST / "PROMOTION_REVIEW.json", review)
    write_private(AUTH_DEST / "PROMOTION_REVIEW.json", review)
    write_repo(REPO_ARTIFACTS / "promotion_review_receipt.json", review)
    write_repo(REPO_ARTIFACTS / "promotion_validation_replay.json", replay_artifact)
    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-two-stage-promotion-review-receipt-20260930.json",
        review,
    )

    summary = {
        "BEST": "UNCHANGED",
        "NEXT_ACTION": review["NEXT_ACTION"],
        "PROMOTION_DECISION": review["PROMOTION_DECISION"],
        "PROMOTION_REVIEW": review["PROMOTION_REVIEW"],
        "RESERVE": "unused",
        "SELECTED_CHECKPOINT_SHA256": EXPECTED_SELECTED_CHECKPOINT_SHA256,
        "TRAIN": False,
        "architecture_pass": architecture["pass"],
        "integrity_pass": integrity["pass"],
        "replay_hash": replay_artifact["replay_hash"],
        "replay_pass": replay_artifact["pass"],
        "review_receipt_sha256": review["review_receipt_sha256"],
        "recommended_pointer": review["best_semantics"]["recommendation"],
    }
    write_private(REVIEW_DEST / "SUMMARY.json", summary)
    write_repo(REPO_ARTIFACTS / "promotion_review_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if review["PROMOTION_DECISION"] == "PROMOTION_READY" else 2


def main() -> int:
    if os.environ.get("HLX_V5_STAGE_A_PROMO_REVIEW_INNER") == "1":
        return inner()

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
        "HLX_V5_STAGE_A_PROMO_REVIEW_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v5_stage_a_two_stage_promotion_review.py"
        ),
    ]
    print(json.dumps({"launch": cmd[-1], "image": IMAGE}, sort_keys=True), flush=True)
    REVIEW_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    log_path = REVIEW_DEST / "promotion_review_console.log"
    with log_path.open("w", encoding="utf-8") as log_handle:
        completed = subprocess.run(
            cmd, check=False, stdout=log_handle, stderr=subprocess.STDOUT
        )
    try:
        print(log_path.read_text(encoding="utf-8")[-12000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
