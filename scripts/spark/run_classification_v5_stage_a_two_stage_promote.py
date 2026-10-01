"""PROMOTE_V5_STAGE_A_TWO_STAGE_SELECTED — apply STAGE_A_BEST component promotion.

Does not retrain, alter thresholds, score reserve, or mutate model-wide BEST.
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
SELECTED_PUBLISHED = Path(
    "/home/morpheus/.hyperlex/models/"
    "hyperlex-encoder-modernbert-base-seed-classification-v5-stage-a-two-stage-001"
)
TRAIN_RECEIPT = RUN_ROOT / "RUN_RECEIPT.json"
REVIEW_DEST = AUTH_DEST / "promotion_review"
PROMOTION_REVIEW = REVIEW_DEST / "PROMOTION_REVIEW.json"
VALIDATION_REPLAY = REVIEW_DEST / "VALIDATION_REPLAY.json"
PROMOTE_DEST = AUTH_DEST / "promotion"
MODELS = Path("/home/morpheus/.hyperlex/models")
BEST_LINK = MODELS / "BEST"
BEST_PATH_FILE = MODELS / "BEST.path"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
STAGE_A_BEST_LINK = MODELS / "STAGE_A_BEST"
STAGE_A_BEST_PATH_FILE = MODELS / "STAGE_A_BEST.path"
STAGE_A_BEST_POINTER = MODELS / "STAGE_A_BEST.json"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
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
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except PermissionError:
        completed = subprocess.run(
            ["sudo", "-n", "cat", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(completed.stdout)


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
        return "UNKNOWN"


def read_previous_stage_a_best() -> str | None:
    if STAGE_A_BEST_POINTER.exists():
        try:
            payload = load_json(STAGE_A_BEST_POINTER)
            return payload.get("STAGE_A_BEST") or payload.get("checkpoint_sha256")
        except (OSError, json.JSONDecodeError):
            pass
    if STAGE_A_BEST_PATH_FILE.exists():
        return "POINTER_PRESENT_WITHOUT_JSON"
    return None


def install_stage_a_best_pointer(pointer: dict) -> None:
    """Create STAGE_A_BEST symlink + path file. Never touch model-wide BEST."""
    target = SELECTED_PUBLISHED
    if not (target / "model.safetensors").exists():
        fail(f"published_selected_missing:{target}")
    if sudo_sha256(target / "model.safetensors") != pointer["checkpoint_sha256"]:
        fail("published_selected_sha_mismatch")

    # Refuse to mutate BEST.
    if BEST_LINK.exists() or BEST_LINK.is_symlink():
        if BEST_LINK.resolve() != Path(
            "/home/morpheus/.hyperlex/models/"
            "hyperlex-encoder-modernbert-base-seed-select004"
        ):
            # Still ok if path text matches expected BEST; check digest instead.
            pass
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_during_promotion")

    if STAGE_A_BEST_LINK.exists() or STAGE_A_BEST_LINK.is_symlink():
        STAGE_A_BEST_LINK.unlink()
    STAGE_A_BEST_LINK.symlink_to(target)
    STAGE_A_BEST_PATH_FILE.write_text(str(target) + "\n", encoding="utf-8")
    os.chmod(STAGE_A_BEST_PATH_FILE, 0o644)
    write_private(STAGE_A_BEST_POINTER, pointer)
    # Public-readable pointer copy for operators.
    write_repo(MODELS / "STAGE_A_BEST.public.json", pointer)


def restore_previous_pointer(previous: str | None) -> None:
    if previous is None:
        if STAGE_A_BEST_LINK.exists() or STAGE_A_BEST_LINK.is_symlink():
            STAGE_A_BEST_LINK.unlink()
        if STAGE_A_BEST_PATH_FILE.exists():
            STAGE_A_BEST_PATH_FILE.unlink()
        if STAGE_A_BEST_POINTER.exists():
            STAGE_A_BEST_POINTER.unlink()
        return
    # Previous non-null pointer restore is out of scope for first promotion.
    fail(f"cannot_auto_restore_previous_stage_a_best:{previous}")


def cold_load_via_canonical_path() -> dict:
    """Load through promoted sequence: trunk → BEST → STAGE_A_BEST → heads."""
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file

    from hyperlexical.classification_v5_stage_a_two_stage import (
        gate1_probabilities,
        gate2_probabilities,
    )
    from hyperlexical.classification_v5_stage_a_two_stage_promote import (
        CANONICAL_GATE1_THRESHOLD,
        CANONICAL_GATE2_THRESHOLD,
        STAGE_A_BEST_SHA256,
        decide_canonical_stage_a,
        post_promotion_replay_check,
        verify_canonical_overlay,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    stage_a_weights = STAGE_A_BEST_LINK / "model.safetensors"
    if not stage_a_weights.exists():
        # Fallback to published path before symlink exists (preflight cold-load).
        stage_a_weights = SELECTED_PUBLISHED / "model.safetensors"
    if not stage_a_weights.exists():
        stage_a_weights = SELECTED

    ckpt_sha = sha256_file(stage_a_weights) if stage_a_weights.stat().st_uid == os.getuid() else sudo_sha256(stage_a_weights)
    if ckpt_sha != STAGE_A_BEST_SHA256:
        fail(f"stage_a_best_sha_mismatch:{ckpt_sha}")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_before_canonical_load")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("promotion cold-load requires CUDA")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    gate1_head = nn.Linear(HIDDEN, 2)
    gate2_head = nn.Linear(HIDDEN, 2)

    best_split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    best_loaded = apply_encoder_trainable(encoder, best_split.get("encoder") or {})
    if best_loaded["loaded"] != 48:
        fail(f"BEST_encoder_overlay_incomplete:{best_loaded['loaded']}")

    tensors = load_file(str(stage_a_weights), device="cpu")
    overlay = verify_canonical_overlay(
        parent_best_sha256=BEST_SHA,
        stage_a_tensor_keys=list(tensors.keys()),
    )
    if not overlay["pass"]:
        fail(f"canonical_overlay_fail:{json.dumps(overlay['checks'], sort_keys=True)}")
    if any(k.startswith("evidence_head.") for k in tensors.keys()):
        fail("flat_evidence_head_present_in_canonical_load")

    split = split_weight_tensors(tensors)
    loaded = apply_encoder_trainable(encoder, split.get("encoder") or {})
    if loaded["loaded"] != 12:
        fail(f"stage_a_overlay_incomplete:{loaded['loaded']}")
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
            # Contract smoke: decide_canonical_stage_a uses frozen thresholds.
            _ = decide_canonical_stage_a(
                p_possible=float(g1["POSSIBLE_EVIDENCE"]),
                p_confirmed=float(g2["CONFIRMED_PRESENT"]),
            )
            golds.append(str(row["evidence_label"]))
            p_possible.append(float(g1["POSSIBLE_EVIDENCE"]))
            p_confirmed.append(float(g2["CONFIRMED_PRESENT"]))

    replay = post_promotion_replay_check(
        golds=golds, p_possible=p_possible, p_confirmed=p_confirmed
    )
    replay["overlay"] = overlay
    replay["n_validation"] = len(rows)
    replay["stage_a_best_sha256"] = ckpt_sha
    replay["thresholds"] = {
        "gate1_threshold": CANONICAL_GATE1_THRESHOLD,
        "gate2_threshold": CANONICAL_GATE2_THRESHOLD,
    }
    return replay


def inner() -> int:
    from hyperlexical.classification_v5_stage_a_two_stage_promote import (
        STAGE_A_BEST_SHA256,
        build_promotion_receipt,
        build_stage_a_best_pointer,
        preflight_promotion,
        utc_now_iso,
    )

    for path in (
        DATASET,
        SELECTED,
        TRAIN_RECEIPT,
        PROMOTION_REVIEW,
        VALIDATION_REPLAY,
        BEST_WEIGHTS,
        SELECTED_PUBLISHED / "model.safetensors",
    ):
        if not path.exists():
            fail(f"missing_required_artifact:{path}")

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset_digest_mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_preflight")
    selected_sha = sha256_file(SELECTED)
    if selected_sha != STAGE_A_BEST_SHA256:
        fail(f"selected_sha_mismatch:{selected_sha}")
    if sudo_sha256(SELECTED_PUBLISHED / "model.safetensors") != STAGE_A_BEST_SHA256:
        fail("published_selected_sha_mismatch")

    review = load_json(PROMOTION_REVIEW)
    replay_art = load_json(VALIDATION_REPLAY)
    train_receipt = load_json(TRAIN_RECEIPT)
    previous = read_previous_stage_a_best()

    preflight = preflight_promotion(
        promotion_review=review,
        validation_replay=replay_art,
        train_receipt=train_receipt,
        selected_checkpoint_sha256=selected_sha,
        model_wide_best_sha256=BEST_SHA,
    )
    if not preflight["pass"]:
        write_private(PROMOTE_DEST / "PREFLIGHT_FAIL.json", preflight)
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return 2

    # Pre-mutation cold-loadability via published selected path.
    pre_replay = cold_load_via_canonical_path()
    if not pre_replay["pass"]:
        fail(f"pre_mutation_cold_load_fail:{pre_replay.get('replay_hash')}")

    promoted_at = utc_now_iso()
    revision = code_revision()
    pointer = build_stage_a_best_pointer(
        weights_path=str(SELECTED_PUBLISHED / "model.safetensors"),
        previous_stage_a_best=previous,
        code_revision=revision,
        promoted_at=promoted_at,
    )
    install_stage_a_best_pointer(pointer)

    # Post-promotion canonical load through STAGE_A_BEST symlink.
    post_replay = cold_load_via_canonical_path()
    overlay = post_replay.pop("overlay")

    if not post_replay["pass"]:
        restore_previous_pointer(previous)
        receipt = build_promotion_receipt(
            preflight=preflight,
            pointer=pointer,
            overlay=overlay,
            post_replay=post_replay,
            previous_stage_a_best=previous,
            code_revision=revision,
            promoted_at=promoted_at,
        )
        write_private(PROMOTE_DEST / "PROMOTION_INVALID.json", receipt)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 2

    # BEST still untouched.
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_after_promotion")
    if BEST_PATH_FILE.read_text(encoding="utf-8").strip() != str(
        Path(
            "/home/morpheus/.hyperlex/models/"
            "hyperlex-encoder-modernbert-base-seed-select004"
        )
    ):
        fail("BEST_path_mutated")

    receipt = build_promotion_receipt(
        preflight=preflight,
        pointer=pointer,
        overlay=overlay,
        post_replay=post_replay,
        previous_stage_a_best=previous,
        code_revision=revision,
        promoted_at=promoted_at,
    )
    PROMOTE_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(PROMOTE_DEST / "STAGE_A_BEST.json", pointer)
    write_private(PROMOTE_DEST / "STAGE_A_PROMOTION.json", receipt)
    write_private(PROMOTE_DEST / "POST_PROMOTION_REPLAY.json", post_replay)
    write_private(AUTH_DEST / "STAGE_A_PROMOTION.json", receipt)
    write_repo(REPO_ARTIFACTS / "stage_a_best_pointer.json", pointer)
    write_repo(REPO_ARTIFACTS / "stage_a_promotion_receipt.json", receipt)
    write_repo(REPO_ARTIFACTS / "stage_a_post_promotion_replay.json", post_replay)
    write_repo(
        SPEC_DIR / "classification-v5-stage-a-two-stage-promotion-receipt-20260930.json",
        receipt,
    )
    write_repo(
        SPEC_DIR / "classification-v5-stage-a-best-pointer-20260930.json",
        pointer,
    )

    summary = {
        "BEST_MUTATED": False,
        "MODEL_WIDE_BEST": BEST_SHA,
        "NEXT_ACTION": receipt["NEXT_ACTION"],
        "RESERVE_CONSUMED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_PROMOTION": receipt["STAGE_A_PROMOTION"],
        "STAGE_A_PROMOTION_RECEIPT_SHA256": receipt[
            "STAGE_A_PROMOTION_RECEIPT_SHA256"
        ],
        "TRAIN": False,
        "post_replay_hash": post_replay["replay_hash"],
        "post_replay_pass": post_replay["pass"],
        "previous_STAGE_A_BEST": previous,
    }
    write_private(PROMOTE_DEST / "SUMMARY.json", summary)
    write_repo(REPO_ARTIFACTS / "stage_a_promotion_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if receipt["STAGE_A_PROMOTION"] == "APPLIED" else 2


def main() -> int:
    if os.environ.get("HLX_V5_STAGE_A_PROMOTE_INNER") == "1":
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
        "HLX_V5_STAGE_A_PROMOTE_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v5_stage_a_two_stage_promote.py"),
    ]
    print(json.dumps({"launch": cmd[-1], "image": IMAGE}, sort_keys=True), flush=True)
    PROMOTE_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    log_path = PROMOTE_DEST / "promotion_console.log"
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
