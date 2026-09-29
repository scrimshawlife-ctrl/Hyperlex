"""Finish validation calibration for the saved Classification v2 checkpoint.

The training run restored epoch 8 and then stopped in NLL underflow.
This loads that checkpoint, scores ordinary validation rows, and writes
the frozen calibration artifact. It does not train, move BEST, or read
the evaluation reserve.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
EXPORT = Path("/home/morpheus/hlx-private/classification-v2-validation-20260929/civilian.v0.2.jsonl")
EXPORT_SHA = "595440b53664b1c9433b5d535cd59778c62b0cf932df0c5a1b434003c211effa"
OUT = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-classification-v2-ready"
)
PRIMARY_SHA = "a8d50a4dcb4d886b3a5daae5740abaae9390595fdbee007da7b0c0372571b4b9"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
PRIVATE = Path("/home/morpheus/hlx-private/classification-v2-train-ready-20260929")

sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sudo_sha256(path: Path) -> str:
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


def inner() -> int:
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.classification_v2 import ACTIVE_FAMILY_VOCABULARY, freeze_calibration
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors
    from hyperlexical.training_routing import route_rows

    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if sha256_file(OUT / "model.safetensors") != PRIMARY_SHA:
        fail("primary checkpoint changed")
    if sha256_file(EXPORT) != EXPORT_SHA:
        fail("validation export changed")
    progress = [
        json.loads(line)
        for line in (OUT / "epoch-progress.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    best = [row for row in progress if row.get("saved_best")][-1]
    if best.get("epoch") != 8 or abs(best["selection_score"] - 0.4254809855319254) > 1e-12:
        fail("best epoch record moved")
    rows = []
    with EXPORT.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    validation = route_rows(rows)[0]["classify"]["val"]
    prohibited = {"held_out", "evaluation_reserve", "settlement", "measurement"}
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(TRUNK)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(TRUNK)
    freeze_encoder(encoder)
    tensors = split_weight_tensors(load_file(OUT / "model.safetensors"))
    loaded = apply_encoder_trainable(encoder, tensors["encoder"])
    if loaded["loaded"] != 12:
        fail(f"encoder overlay loaded {loaded['loaded']} tensors")
    applicability = torch.nn.Linear(HIDDEN, 2)
    family = torch.nn.Linear(HIDDEN, len(ACTIVE_FAMILY_VOCABULARY))
    applicability.load_state_dict(tensors["applicability"])
    family.load_state_dict(tensors["family_head"])
    encoder.to(device).eval()
    applicability.to(device).eval()
    family.to(device).eval()
    applicability_rows = []
    family_rows = []
    with torch.no_grad():
        for row in validation:
            if (
                row.get("split") == "test"
                or row.get("evaluation_reserve")
                or row.get("held_out")
                or row.get("surface") in prohibited
            ):
                fail("calibration refused a non-validation row")
            lineage = row.get("lineage")
            if lineage not in ACTIVE_FAMILY_VOCABULARY and lineage != "none":
                continue
            encoded = tokenizer(
                [row["text"]],
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            applicability_rows.append(
                (
                    [float(value) for value in applicability(pooled)[0].detach().cpu()],
                    0 if lineage == "none" else 1,
                )
            )
            if lineage in ACTIVE_FAMILY_VOCABULARY:
                family_rows.append(
                    (
                        [float(value) for value in family(pooled)[0].detach().cpu()],
                        ACTIVE_FAMILY_VOCABULARY.index(lineage),
                    )
                )
    artifact = freeze_calibration(
        applicability_rows=applicability_rows,
        family_rows=family_rows,
        surface="validation",
        checkpoint_identity=best.get("checkpoint_sha256"),
    )
    if artifact["reserve_used"] or artifact["training_rows_used"] or artifact["surface"] != "validation":
        fail("calibration artifact left the validation surface")
    destination = OUT / "classification-v2-calibration.json"
    destination.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(artifact, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_CALIBRATE_INNER") == "1":
        return inner()
    if (OUT / "classification-v2-calibration.json").exists():
        fail("calibration artifact already exists")
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-classification-v2-calibrate-ready",
        "-v",
        "/home/morpheus/Hyperlex:/home/morpheus/Hyperlex",
        "-v",
        "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-w",
        "/home/morpheus/Hyperlex",
        "-e",
        "HOME=/home/morpheus",
        "-e",
        "HF_HUB_OFFLINE=1",
        "-e",
        "TRANSFORMERS_OFFLINE=1",
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "PYTHONUNBUFFERED=1",
        "-e",
        "HLX_CALIBRATE_INNER=1",
        IMAGE,
        "python",
        "-u",
        "scripts/spark/calibrate_classification_v2_ready.py",
    ]
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    log_path = PRIVATE / "calibrate.log"
    print(json.dumps({"calibrating": str(OUT)}, sort_keys=True), flush=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    if completed.returncode != 0:
        fail(f"calibration exit {completed.returncode}")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during calibration")
    if sudo_sha256(OUT / "model.safetensors") != PRIMARY_SHA:
        fail("primary checkpoint changed during calibration")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
