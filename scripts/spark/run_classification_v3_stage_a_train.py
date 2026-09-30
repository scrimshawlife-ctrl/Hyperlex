"""Train Classification v3 Stage A once on the READY evidence surface.

Primary validation gate: false_evidence_entry_rate_on_none <= 0.05.
Does not create a v3 reserve, does not score the spent v2 reserve, and does not
move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
SURFACE = Path("/home/morpheus/hlx-private/classification-v3-evidence-surface-20260930")
SURFACE_DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
SURFACE_DATASET_SHA = "7339c044596a4cc2eb5ae17f3fbab185fface9abffb6151bdb0db69eca0d2d3a"
SURFACE_READINESS_SHA = "89a82318689b6deaeb7fe4681b4e0981f5f46fb224ebd03dce79726e6db7c53d"
PRIVATE = Path("/home/morpheus/hlx-private/classification-v3-stage-a-20260930")
OUT = Path(
    "/home/morpheus/.hyperlex/models/"
    "hyperlex-encoder-modernbert-base-seed-classification-v3-stage-a"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
BEST_LINK = Path("/home/morpheus/.hyperlex/models/BEST")
INIT_FROM = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004"
)
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
DEST = PRIVATE / "STAGE_A_TRAIN.json"

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
        pass
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
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def pin_inputs() -> dict:
    if sha256_file(SURFACE_DATASET) != SURFACE_DATASET_SHA:
        fail("evidence surface dataset digest mismatch")
    readiness = json.loads((SURFACE / "READINESS.json").read_text(encoding="utf-8"))
    if readiness.get("receipt_sha256") != SURFACE_READINESS_SHA:
        fail("evidence surface readiness digest mismatch")
    if readiness.get("readiness", {}).get("state") != "READY":
        fail("evidence surface is not READY")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    try:
        best_ok = BEST_LINK.is_symlink() and BEST_LINK.resolve() == INIT_FROM.resolve()
    except PermissionError:
        target = subprocess.run(
            ["sudo", "-n", "readlink", "-f", str(BEST_LINK)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        best_ok = Path(target) == INIT_FROM.resolve()
    if not best_ok:
        fail("BEST symlink is not the production checkpoint")
    if OUT.exists():
        fail(f"output already exists: {OUT}")
    return {"readiness": readiness}


def load_surface_rows() -> tuple[list[dict], list[dict]]:
    rows = [
        json.loads(line)
        for line in SURFACE_DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    train = [row for row in rows if row.get("split") == "train"]
    val = [row for row in rows if row.get("split") == "validation"]
    if len(train) < 500 or len(val) < 100:
        fail(f"surface split too small train={len(train)} val={len(val)}")
    return train, val


def inner() -> int:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file, save_file

    from hyperlexical.classification_v3_evidence_gate import EVIDENCE_LABELS
    from hyperlexical.classification_v3_stage_a import (
        TRAIN_HYPERPARAMS,
        assemble_stage_a_receipt,
        calibrate_thresholds,
        evidence_score_from_probabilities,
        evaluate_decisions,
        label_index,
        next_action_for_stage_a,
        softmax_logits,
        stage_a_contract,
        stratified_label_indices,
        canonical_json,
        sha256_text,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import (
        collect_encoder_trainable,
        flatten_weight_tensors,
        split_weight_tensors,
    )

    pin_inputs()
    train_rows, val_rows = load_surface_rows()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("Stage A train requires CUDA")

    torch.manual_seed(int(TRAIN_HYPERPARAMS["seed"]))
    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    warm = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    loaded = apply_encoder_trainable(encoder, warm.get("encoder") or {})
    if loaded["loaded"] != 48:
        fail(f"BEST encoder overlay missed tensors: loaded={loaded['loaded']}")
    trainable_params, last_n = freeze_encoder(
        encoder, last_trainable=int(TRAIN_HYPERPARAMS["last_trainable"])
    )
    evidence_head = nn.Linear(HIDDEN, len(EVIDENCE_LABELS))
    encoder.to(device)
    evidence_head.to(device)
    optimizer = torch.optim.AdamW(
        [param for param in list(encoder.parameters()) + list(evidence_head.parameters()) if param.requires_grad],
        lr=float(TRAIN_HYPERPARAMS["learning_rate"]),
        weight_decay=float(TRAIN_HYPERPARAMS["weight_decay"]),
    )
    loss_fn = nn.CrossEntropyLoss()

    train_labels = [str(row["evidence_label"]) for row in train_rows]
    encoder.train()
    evidence_head.train()
    epoch_losses = []
    for epoch in range(int(TRAIN_HYPERPARAMS["epochs"])):
        batches = stratified_label_indices(
            train_labels,
            batch_size=int(TRAIN_HYPERPARAMS["batch_size"]),
            seed=int(TRAIN_HYPERPARAMS["seed"]) + epoch,
        )
        running = 0.0
        n_batches = 0
        for batch_indices in batches:
            texts = [str(train_rows[i]["text"]) for i in batch_indices]
            targets = torch.tensor(
                [label_index(train_labels[i]) for i in batch_indices],
                dtype=torch.long,
                device=device,
            )
            encoded = tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=int(TRAIN_HYPERPARAMS["max_len"] or MAX_LEN),
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            logits = evidence_head(pooled)
            loss = loss_fn(logits, targets)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            running += float(loss.detach().cpu())
            n_batches += 1
        epoch_losses.append(running / max(1, n_batches))
        print(
            json.dumps(
                {"epoch": epoch + 1, "mean_loss": epoch_losses[-1], "n_batches": n_batches},
                sort_keys=True,
            ),
            flush=True,
        )

    def score_split(rows: list[dict]) -> tuple[list[str], list[float], list[str], list[str]]:
        encoder.eval()
        evidence_head.eval()
        golds = []
        scores = []
        subtypes = []
        argmax_preds = []
        with torch.no_grad():
            for row in rows:
                encoded = tokenizer(
                    [str(row["text"])],
                    padding=True,
                    truncation=True,
                    max_length=int(TRAIN_HYPERPARAMS["max_len"] or MAX_LEN),
                    return_tensors="pt",
                )
                encoded = {key: value.to(device) for key, value in encoded.items()}
                pooled = encoder(**encoded).last_hidden_state[:, 0]
                logits = evidence_head(pooled)[0].detach().cpu().tolist()
                probs = softmax_logits(logits)
                golds.append(str(row["evidence_label"]))
                scores.append(evidence_score_from_probabilities(probs))
                subtypes.append(str(row["evidence_subtype"]))
                argmax_preds.append(max(probs, key=probs.get))
        return golds, scores, subtypes, argmax_preds

    train_golds, train_scores, train_subtypes, train_argmax = score_split(train_rows)
    val_golds, val_scores, val_subtypes, val_argmax = score_split(val_rows)
    train_argmax_metrics = evaluate_decisions(
        train_golds, train_argmax, subtypes=train_subtypes
    )
    val_argmax_metrics = evaluate_decisions(val_golds, val_argmax, subtypes=val_subtypes)
    calibration = calibrate_thresholds(val_golds, val_scores, subtypes=val_subtypes)
    next_action = next_action_for_stage_a(
        primary_gate_pass=bool(calibration["metrics"]["primary_gate_pass"])
    )

    OUT.mkdir(parents=True, exist_ok=True)
    os.chmod(OUT, 0o755)
    encoder_tensors = collect_encoder_trainable(encoder)
    flat = flatten_weight_tensors(
        {
            "encoder": encoder_tensors,
            "evidence_head": {
                "weight": evidence_head.weight.detach().cpu().contiguous(),
                "bias": evidence_head.bias.detach().cpu().contiguous(),
            },
        }
    )
    weights_path = OUT / "model.safetensors"
    save_file(flat, str(weights_path))
    config = {
        "evidence_labels": list(EVIDENCE_LABELS),
        "hidden_size": HIDDEN,
        "init_from": str(INIT_FROM),
        "last_trainable": last_n,
        "rule": stage_a_contract()["rule"],
        "schema": "hyperlex.classification.v3.stage_a_config.v1",
        "surface_dataset_sha256": SURFACE_DATASET_SHA,
        "trainable_encoder_params": trainable_params,
    }
    config_path = OUT / "stage_a_config.json"
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    calibration_path = OUT / "stage_a_calibration.json"
    calibration_body = {
        "none_threshold": calibration["chosen"]["none_threshold"],
        "present_threshold": calibration["chosen"]["present_threshold"],
        "primary_gate_pass": calibration["metrics"]["primary_gate_pass"],
        "false_evidence_entry_rate_on_none": calibration["metrics"][
            "false_evidence_entry_rate_on_none"
        ],
        "selection_rule": calibration["selection_rule"],
        "surface": "validation",
        "reserve_used": False,
    }
    calibration_path.write_text(
        json.dumps(calibration_body, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    checkpoint_sha = sha256_file(weights_path)
    config_sha = sha256_file(config_path)
    receipt = assemble_stage_a_receipt(
        {
            "best_sha256": BEST_SHA,
            "calibration": calibration,
            "checkpoint_sha256": checkpoint_sha,
            "config_sha256": config_sha,
            "dataset_sha256": SURFACE_DATASET_SHA,
            "next_action": next_action,
            "train_metrics": {
                "argmax": train_argmax_metrics,
                "epoch_losses": epoch_losses,
            },
            "weights_dir": str(OUT),
        }
    )
    receipt["validation_argmax"] = val_argmax_metrics
    receipt["contract"] = stage_a_contract()
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    write_private(DEST, receipt)
    write_private(PRIVATE / "CALIBRATION.json", calibration)
    write_private(PRIVATE / "CONFIG.json", config)
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during Stage A train")
    print(
        json.dumps(
            {
                "checkpoint_sha256": checkpoint_sha,
                "destination": str(DEST),
                "false_evidence_entry_rate_on_none": calibration["metrics"][
                    "false_evidence_entry_rate_on_none"
                ],
                "next_action": next_action,
                "none_threshold": calibration["chosen"]["none_threshold"],
                "present_f1": calibration["chosen"]["present_f1"],
                "present_threshold": calibration["chosen"]["present_threshold"],
                "primary_gate_pass": calibration["metrics"]["primary_gate_pass"],
                "receipt_sha256": receipt["receipt_sha256"],
                "uncertain_rate": calibration["metrics"]["uncertain_rate"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    if "--inner" in sys.argv:
        return inner()
    pinned = pin_inputs()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(
        PRIVATE / "LAUNCH.json",
        {
            "authorization": "TRAIN_STAGE_A_ONCE_AGAINST_PREREGISTERED_FALSE_ENTRY_GATE",
            "best_sha256": BEST_SHA,
            "dataset_sha256": SURFACE_DATASET_SHA,
            "moves_best": False,
            "readiness_receipt_sha256": SURFACE_READINESS_SHA,
            "reserve": None,
            "surface_ready": pinned["readiness"]["readiness"]["state"],
            "train": True,
            "v3_reserve": None,
        },
    )
    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--name",
        "hlx-classification-v3-stage-a",
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
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "PYTHONUNBUFFERED=1",
        "-e",
        "TRANSFORMERS_OFFLINE=1",
        IMAGE,
        "python3",
        "-u",
        str(REPO / "scripts/spark/run_classification_v3_stage_a_train.py"),
        "--inner",
    ]
    log_path = PRIVATE / "stage_a_train.log"
    print(json.dumps({"launching": str(DEST), "log": str(log_path)}), flush=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    write_private(PRIVATE / "EXIT.json", {"code": completed.returncode})
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed during Stage A train")
    if completed.returncode != 0:
        fail(f"Stage A train exit {completed.returncode}; see {log_path}")
    artifact = json.loads(sudo_read_text(DEST))
    print(
        json.dumps(
            {
                "checkpoint_sha256": artifact["checkpoint_sha256"],
                "destination": str(DEST),
                "false_evidence_entry_rate_on_none": artifact["validation_metrics"][
                    "false_evidence_entry_rate_on_none"
                ],
                "next_action": artifact["next_action"],
                "primary_gate_pass": artifact["primary_gate_pass"],
                "receipt_sha256": artifact["receipt_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
