"""TRAIN_V5_STAGE_A_ONCE — fail-closed single authorized Stage-A train.

Requires sealed AUTHORIZATION.json. Does not move BEST. Does not consume reserve.
Set HLX_V5_STAGE_A_EXECUTE_TRAIN=1 to execute the one authorized run.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-negative-evidence-surface-v1r7-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
AUTH_DEST = Path("/home/morpheus/hlx-private/classification-v5-stage-a-train-20260930")
AUTH_FILE = AUTH_DEST / "AUTHORIZATION.json"
RESOLVED = AUTH_DEST / "RESOLVED_TRAINING_CONFIG.json"
LABEL_PROVENANCE = AUTH_DEST / "LABEL_PROVENANCE.jsonl"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
INIT_FROM = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004"
)
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
OUT = Path(
    "/home/morpheus/.hyperlex/models/"
    "hyperlex-encoder-modernbert-base-seed-classification-v5-stage-a"
)
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"

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


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def require_authorization() -> dict:
    from hyperlexical.classification_v5_stage_a import (
        AUTHORIZED_DATASET_SHA,
        authorization_gate_checks,
    )

    if not AUTH_FILE.exists() or not RESOLVED.exists():
        fail("authorization artifacts missing; run authorize first")
    auth = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    resolved = json.loads(RESOLVED.read_text(encoding="utf-8"))
    dataset_sha = sha256_file(DATASET)
    readiness = json.loads((SURFACE / "READINESS.json").read_text(encoding="utf-8"))
    surface_state = "PASS" if readiness.get("state") == "READY" else "FAIL"
    current_best = sudo_sha256(BEST_WEIGHTS)
    gate = authorization_gate_checks(
        train_authorized=bool(auth.get("TRAIN_AUTHORIZED") or auth.get("train_authorized")),
        dataset_sha256=dataset_sha,
        surface_readiness=surface_state,
        resolved_config_sha256=resolved.get("training_config_sha256"),
        authorized_config_sha256=auth.get("TRAINING_CONFIG_SHA256"),
        current_best=current_best,
        reserve_consumed=bool(auth.get("RESERVE_CONSUMED", True)),
    )
    if dataset_sha != AUTHORIZED_DATASET_SHA:
        fail(f"dataset not authorized:{dataset_sha}")
    if not gate["pass"]:
        fail(f"authorization_gate_failed:{json.dumps(gate['checks'], sort_keys=True)}")
    if auth.get("TRAINING_STATUS") not in {"AUTHORIZED_NOT_STARTED", "RUNNING"}:
        fail(f"training_status_blocked:{auth.get('TRAINING_STATUS')}")
    if not LABEL_PROVENANCE.exists():
        fail("label provenance sidecar missing")
    return {"auth": auth, "resolved": resolved, "gate": gate, "dataset_sha": dataset_sha}


def inner() -> int:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file, save_file

    from hyperlexical.classification_v5_stage_a import (
        EVIDENCE_LABELS,
        TRAIN_HYPERPARAMS,
        calibrate_thresholds,
        decide_evidence,
        evidence_score_from_probabilities,
        evaluate_decisions,
        label_index,
        softmax_logits,
        stage_a_macro_f1,
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

    pins = require_authorization()
    resolved = pins["resolved"]
    auth = pins["auth"]
    if OUT.exists():
        fail(f"output already exists:{OUT}")

    rows = load_jsonl(DATASET)
    train_rows = [row for row in rows if row.get("split") == "train"]
    val_rows = [row for row in rows if row.get("split") == "validation"]
    class_weights = resolved["class_weight_report"]["class_weights"]
    prov_mult = resolved["loss"]["provenance_multipliers"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("Stage A train requires CUDA")

    seed = int(TRAIN_HYPERPARAMS["seed"])
    torch.manual_seed(seed)
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
    nn.init.xavier_uniform_(evidence_head.weight)
    nn.init.zeros_(evidence_head.bias)
    encoder.to(device)
    evidence_head.to(device)
    optimizer = torch.optim.AdamW(
        [
            param
            for param in list(encoder.parameters()) + list(evidence_head.parameters())
            if param.requires_grad
        ],
        lr=float(TRAIN_HYPERPARAMS["learning_rate"]),
        weight_decay=float(TRAIN_HYPERPARAMS["weight_decay"]),
    )
    weight_tensor = torch.tensor(
        [float(class_weights[label]) for label in EVIDENCE_LABELS],
        dtype=torch.float32,
        device=device,
    )
    loss_fn = nn.CrossEntropyLoss(weight=weight_tensor, reduction="none")

    train_labels = [str(row["evidence_label"]) for row in train_rows]
    max_epochs = int(TRAIN_HYPERPARAMS["max_epochs"])
    min_epochs = int(TRAIN_HYPERPARAMS["minimum_epochs"])
    patience = int(TRAIN_HYPERPARAMS["early_stopping_patience"])
    batch_size = int(TRAIN_HYPERPARAMS["micro_batch_size"])
    max_len = int(TRAIN_HYPERPARAMS["max_len"] or MAX_LEN)

    best_state = None
    best_epoch = 0
    best_macro = -1.0
    best_false_entry = 1.0
    best_none_recall = -1.0
    stale = 0
    epoch_trace = []
    started = time.time()

    def score_split(split_rows: list[dict]):
        encoder.eval()
        evidence_head.eval()
        golds, scores, subtypes, argmax_preds = [], [], [], []
        with torch.no_grad():
            for row in split_rows:
                encoded = tokenizer(
                    [str(row["text"])],
                    padding=True,
                    truncation=True,
                    max_length=max_len,
                    return_tensors="pt",
                )
                encoded = {k: v.to(device) for k, v in encoded.items()}
                pooled = encoder(**encoded).last_hidden_state[:, 0]
                logits = evidence_head(pooled)[0].detach().cpu().tolist()
                probs = softmax_logits(logits)
                golds.append(str(row["evidence_label"]))
                scores.append(evidence_score_from_probabilities(probs))
                subtypes.append(str(row["evidence_subtype"]))
                argmax_preds.append(max(probs, key=probs.get))
        return golds, scores, subtypes, argmax_preds

    for epoch in range(max_epochs):
        encoder.train()
        evidence_head.train()
        batches = stratified_label_indices(
            train_labels, batch_size=batch_size, seed=seed + epoch
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
            sample_w = torch.tensor(
                [
                    float(prov_mult.get(str(train_rows[i].get("provenance")), 0.5))
                    for i in batch_indices
                ],
                dtype=torch.float32,
                device=device,
            )
            encoded = tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=max_len,
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            logits = evidence_head(pooled)
            per_ex = loss_fn(logits, targets) * sample_w
            loss = per_ex.mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                [p for p in list(encoder.parameters()) + list(evidence_head.parameters()) if p.requires_grad],
                float(TRAIN_HYPERPARAMS["max_grad_norm"]),
            )
            optimizer.step()
            running += float(loss.detach().cpu())
            n_batches += 1

        val_golds, val_scores, val_subtypes, val_argmax = score_split(val_rows)
        # Checkpoint selection uses argmax macro-F1 on validation (selection metric),
        # with threshold calibration applied after best-epoch restore.
        macro = stage_a_macro_f1(val_golds, val_argmax)
        argmax_metrics = evaluate_decisions(
            val_golds, val_argmax, subtypes=val_subtypes
        )
        false_entry = argmax_metrics["false_evidence_entry_rate_on_none"]
        none_recall = argmax_metrics["by_label"]["NO_EVIDENCE"]["recall"]
        epoch_trace.append(
            {
                "epoch": epoch + 1,
                "mean_loss": running / max(1, n_batches),
                "n_batches": n_batches,
                "stage_a_macro_f1": macro,
                "false_evidence_entry_rate_on_none": false_entry,
                "NO_EVIDENCE_recall": none_recall,
            }
        )
        print(json.dumps(epoch_trace[-1], sort_keys=True), flush=True)

        improved = False
        if macro > best_macro + 1e-12:
            improved = True
        elif abs(macro - best_macro) <= 1e-12:
            if false_entry < best_false_entry - 1e-12:
                improved = True
            elif abs(false_entry - best_false_entry) <= 1e-12 and none_recall > best_none_recall + 1e-12:
                improved = True
        if improved:
            best_macro = macro
            best_false_entry = false_entry
            best_none_recall = none_recall
            best_epoch = epoch + 1
            best_state = {
                "encoder": {k: v.detach().cpu().clone() for k, v in collect_encoder_trainable(encoder).items()},
                "head_weight": evidence_head.weight.detach().cpu().clone(),
                "head_bias": evidence_head.bias.detach().cpu().clone(),
            }
            stale = 0
        else:
            stale += 1
        if epoch + 1 >= min_epochs and stale >= patience:
            break

    if best_state is None:
        fail("no_best_checkpoint_selected")

    # Restore best checkpoint.
    apply_encoder_trainable(encoder, best_state["encoder"])
    with torch.no_grad():
        evidence_head.weight.copy_(best_state["head_weight"].to(device))
        evidence_head.bias.copy_(best_state["head_bias"].to(device))

    train_golds, train_scores, train_subtypes, train_argmax = score_split(train_rows)
    val_golds, val_scores, val_subtypes, val_argmax = score_split(val_rows)
    calibration = calibrate_thresholds(val_golds, val_scores, subtypes=val_subtypes)
    if not calibration["feasible"]:
        disposition = "SETTLED_FAIL"
        val_metrics = evaluate_decisions(
            val_golds,
            [
                decide_evidence(s, none_threshold=0.5, present_threshold=0.55)
                for s in val_scores
            ],
            subtypes=val_subtypes,
        )
    else:
        disposition = "SETTLED_PASS_CANDIDATE"
        chosen = calibration["chosen"]
        val_decisions = [
            decide_evidence(
                s,
                none_threshold=chosen["none_threshold"],
                present_threshold=chosen["present_threshold"],
            )
            for s in val_scores
        ]
        val_metrics = evaluate_decisions(val_golds, val_decisions, subtypes=val_subtypes)

    OUT.mkdir(parents=True, exist_ok=True)
    os.chmod(OUT, 0o755)
    flat = flatten_weight_tensors(
        {
            "encoder": collect_encoder_trainable(encoder),
            "evidence_head": {
                "weight": evidence_head.weight.detach().cpu().contiguous(),
                "bias": evidence_head.bias.detach().cpu().contiguous(),
            },
        }
    )
    weights_path = OUT / "model.safetensors"
    save_file(flat, str(weights_path))
    config_path = OUT / "stage_a_config.json"
    config_path.write_text(
        json.dumps(
            {
                "best_epoch": best_epoch,
                "evidence_labels": list(EVIDENCE_LABELS),
                "hidden_size": HIDDEN,
                "init_from": str(INIT_FROM),
                "last_trainable": last_n,
                "resolved_training_config_sha256": resolved["training_config_sha256"],
                "rule": auth["rule"],
                "schema": "hyperlex.classification.v5.stage_a_config.v1",
                "seed": seed,
                "surface_dataset_sha256": pins["dataset_sha"],
                "trainable_encoder_params": trainable_params,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = time.time() - started
    receipt = {
        "BEST": "UNCHANGED",
        "BEST_MUTATED": False,
        "CURRENT_BEST": BEST_SHA,
        "EXPERIMENT_ID": auth["EXPERIMENT_ID"],
        "RESERVE_CONSUMED": False,
        "TRAINING_STATUS": "COMPLETE",
        "best_epoch": best_epoch,
        "best_stage_a_macro_f1_argmax": best_macro,
        "calibration": calibration,
        "checkpoint_sha256": sha256_file(weights_path),
        "config_sha256": sha256_file(config_path),
        "dataset_sha256": pins["dataset_sha"],
        "disposition": disposition,
        "epoch_trace": epoch_trace,
        "final_epoch": epoch_trace[-1]["epoch"] if epoch_trace else 0,
        "runtime_seconds": runtime,
        "training_config_sha256": resolved["training_config_sha256"],
        "validation_metrics": val_metrics,
        "weights_dir": str(OUT),
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    write_private(AUTH_DEST / "STAGE_A_TRAIN.json", receipt)
    # Mark authorization consumed for the single run.
    auth["TRAINING_STATUS"] = "COMPLETE"
    auth["train_run_completed"] = True
    write_private(AUTH_FILE, auth)
    print(json.dumps({"TRAINING_STATUS": "COMPLETE", "disposition": disposition, "receipt_sha256": receipt["receipt_sha256"]}, indent=2, sort_keys=True))
    return 0


def main() -> int:
    pins = require_authorization()
    if os.environ.get("HLX_V5_STAGE_A_EXECUTE_TRAIN") != "1":
        print(
            json.dumps(
                {
                    "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
                    "authorization_pass": True,
                    "execute_train": False,
                    "experiment_id": pins["auth"].get("EXPERIMENT_ID"),
                    "message": (
                        "authorization gates passed; set "
                        "HLX_V5_STAGE_A_EXECUTE_TRAIN=1 to run the single train"
                    ),
                    "training_config_sha256": pins["resolved"]["training_config_sha256"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if os.environ.get("HLX_V5_STAGE_A_TRAIN_INNER") == "1":
        return inner()

    # Launch GPU container for the single authorized run.
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
        "HLX_V5_STAGE_A_EXECUTE_TRAIN=1",
        "-e",
        "HLX_V5_STAGE_A_TRAIN_INNER=1",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v5_stage_a_train.py"),
    ]
    print(json.dumps({"launch": cmd[-1], "image": IMAGE}, sort_keys=True), flush=True)
    completed = subprocess.run(cmd, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
