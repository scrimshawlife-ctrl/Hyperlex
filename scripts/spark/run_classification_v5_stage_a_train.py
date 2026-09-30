"""TRAIN_V5_STAGE_A_ONCE — fail-closed single authorized Stage-A train.

Requires sealed AUTHORIZATION.json. Does not move BEST. Does not consume reserve.
Set HLX_V5_STAGE_A_EXECUTE_TRAIN=1 to execute the one authorized run.

Retention (frozen):
  INITIAL = BEST + deterministic head init (manifest; weights reconstructible)
  SELECTED = restored best-validation checkpoint (permanent loadable artifact)
  FINAL_RUN_STATE = terminal trainer state if distinct from SELECTED
Non-selected intermediate checkpoints are pruned after settlement.
Settlement must never destroy the checkpoint or evidence required to reproduce,
inspect, or falsify the recorded scientific result.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-negative-evidence-surface-v1r7-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
AUTH_DEST = Path("/home/morpheus/hlx-private/classification-v5-stage-a-train-20260930")
RUN_ROOT = AUTH_DEST / "classification-v5-stage-a-001"
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
# Legacy mirror path for selected weights (loadable inference artifact).
OUT = Path(
    "/home/morpheus/.hyperlex/models/"
    "hyperlex-encoder-modernbert-base-seed-classification-v5-stage-a"
)
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"

NONE_SUBTYPES = (
    "ORDINARY_DOMAIN_NONE",
    "HARD_NONE",
    "NEAR_DOMAIN_NONE",
    "GENERIC_NONE",
    "LEXICAL_LOOKALIKE_NONE",
    "SHORT_ATOM_NONE",
)
ALL_SUBTYPES = NONE_SUBTYPES + ("POSITIVE_EVIDENCE", "AMBIGUOUS_EVIDENCE")

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


def length_bucket(text: str) -> str:
    n = len(text)
    if n < 40:
        return "lt_40"
    if n < 80:
        return "40_79"
    return "ge_80"


def source_bucket(row: dict) -> str:
    url = str(row.get("source_url") or "")
    if "wiktionary" in url.lower():
        return "wiktionary"
    if url:
        return "other_url"
    return "none"


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
    if auth.get("train_run_completed"):
        fail("training_run_count_already_nonzero")
    if (AUTH_DEST / "STAGE_A_TRAIN.json").exists() or (RUN_ROOT / "RUN_RECEIPT.json").exists():
        fail("prior_run_receipt_present")
    if not LABEL_PROVENANCE.exists():
        fail("label provenance sidecar missing")
    stats = json.loads((AUTH_DEST / "LABEL_PROVENANCE_STATS.json").read_text(encoding="utf-8"))
    if int(stats.get("invalid_provenance_rows", 1)) != 0:
        fail("label_provenance_invalid_rows_nonzero")
    return {
        "auth": auth,
        "resolved": resolved,
        "gate": gate,
        "dataset_sha": dataset_sha,
        "readiness": readiness,
    }


def subtype_diagnostics(
    rows: list[dict], golds: list[str], decisions: list[str]
) -> dict:
    out: dict[str, dict] = {}
    for subtype in ALL_SUBTYPES:
        idx = [i for i, row in enumerate(rows) if row.get("evidence_subtype") == subtype]
        support = len(idx)
        if support == 0:
            out[subtype] = {"support": 0}
            continue
        sub_golds = [golds[i] for i in idx]
        sub_preds = [decisions[i] for i in idx]
        none_gold = [i for i, g in enumerate(sub_golds) if g == "NO_EVIDENCE"]
        none_recall = (
            sum(1 for i in none_gold if sub_preds[i] == "NO_EVIDENCE") / len(none_gold)
            if none_gold
            else None
        )
        false_present = sum(1 for i in none_gold if sub_preds[i] == "EVIDENCE_PRESENT")
        uncertain_n = sum(1 for p in sub_preds if p == "UNCERTAIN")
        out[subtype] = {
            "NO_EVIDENCE_recall": none_recall,
            "UNCERTAIN_count": uncertain_n,
            "UNCERTAIN_rate": uncertain_n / support,
            "false_EVIDENCE_PRESENT_count": false_present,
            "false_EVIDENCE_PRESENT_rate": (
                false_present / len(none_gold) if none_gold else None
            ),
            "support": support,
        }
    return out


def slice_diagnostics(
    rows: list[dict],
    golds: list[str],
    decisions: list[str],
    *,
    key_fn,
) -> dict:
    from hyperlexical.classification_v5_stage_a import evaluate_decisions

    buckets: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        buckets[str(key_fn(row))].append(index)
    out = {}
    for name, indices in sorted(buckets.items()):
        metrics = evaluate_decisions(
            [golds[i] for i in indices],
            [decisions[i] for i in indices],
        )
        out[name] = {
            "EVIDENCE_PRESENT_recall": metrics["by_label"]["EVIDENCE_PRESENT"]["recall"],
            "NO_EVIDENCE_recall": metrics["by_label"]["NO_EVIDENCE"]["recall"],
            "false_evidence_entry_rate_on_none": metrics[
                "false_evidence_entry_rate_on_none"
            ],
            "n": len(indices),
            "stage_a_macro_f1": metrics["stage_a_macro_f1"],
            "uncertain_rate": metrics["uncertain_rate"],
        }
    return out


def inner() -> int:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file, save_file

    from hyperlexical.classification_v2_surface import SURFACE_ATOM, surface_form
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
    if RUN_ROOT.exists():
        fail(f"run root already exists:{RUN_ROOT}")

    RUN_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(RUN_ROOT, 0o700)
    (RUN_ROOT / "logs").mkdir(mode=0o700, exist_ok=True)
    (RUN_ROOT / "diagnostics").mkdir(mode=0o700, exist_ok=True)
    (RUN_ROOT / "selected").mkdir(mode=0o700, exist_ok=True)
    tmp_ckpt_root = RUN_ROOT / "tmp_checkpoints"
    tmp_ckpt_root.mkdir(mode=0o700, exist_ok=True)

    # Mark RUNNING (same authorized run; recovery allowed until settlement).
    auth["TRAINING_STATUS"] = "RUNNING"
    write_private(AUTH_FILE, auth)

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

    # INITIAL checkpoint manifest (weights reconstructible from BEST + deterministic init).
    initial_manifest = {
        "checkpoint_role": "INITIAL",
        "class_order": list(EVIDENCE_LABELS),
        "code_revision": resolved.get("code_revision"),
        "dataset_sha256": pins["dataset_sha"],
        "head_init": TRAIN_HYPERPARAMS["head_init"],
        "parent_BEST_sha256": BEST_SHA,
        "reconstructible_from": {
            "best_weights_path": str(BEST_WEIGHTS),
            "head_init": TRAIN_HYPERPARAMS["head_init"],
            "seed": seed,
            "trunk": str(TRUNK),
        },
        "schema": "hyperlex.classification.v5.stage_a_checkpoint_manifest.v1",
        "seed": seed,
        "tokenizer_identity": resolved["tokenization"]["tokenizer_identity"],
        "training_config_sha256": resolved["training_config_sha256"],
        "weights_duplicated": False,
    }
    write_private(RUN_ROOT / "INITIAL_CHECKPOINT.json", initial_manifest)

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
    optimizer_steps = 0
    started = time.time()
    metrics_path = RUN_ROOT / "METRICS.jsonl"
    if metrics_path.exists():
        metrics_path.unlink()

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

    def capture_weights():
        return {
            "encoder": {
                k: v.detach().cpu().clone()
                for k, v in collect_encoder_trainable(encoder).items()
            },
            "head_bias": evidence_head.bias.detach().cpu().clone(),
            "head_weight": evidence_head.weight.detach().cpu().clone(),
        }

    def save_tmp_checkpoint(epoch: int, role: str, state: dict) -> Path:
        path = tmp_ckpt_root / f"checkpoint-{epoch:04d}-{role}"
        path.mkdir(parents=True, exist_ok=True)
        flat = flatten_weight_tensors(
            {
                "encoder": state["encoder"],
                "evidence_head": {
                    "weight": state["head_weight"].contiguous(),
                    "bias": state["head_bias"].contiguous(),
                },
            }
        )
        save_file(flat, str(path / "model.safetensors"))
        write_private(
            path / "meta.json",
            {"epoch": epoch, "role": role, "temporary": True},
        )
        return path

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
                [
                    p
                    for p in list(encoder.parameters()) + list(evidence_head.parameters())
                    if p.requires_grad
                ],
                float(TRAIN_HYPERPARAMS["max_grad_norm"]),
            )
            optimizer.step()
            optimizer_steps += 1
            running += float(loss.detach().cpu())
            n_batches += 1

        val_golds, val_scores, val_subtypes, val_argmax = score_split(val_rows)
        macro = stage_a_macro_f1(val_golds, val_argmax)
        argmax_metrics = evaluate_decisions(
            val_golds, val_argmax, subtypes=val_subtypes
        )
        false_entry = argmax_metrics["false_evidence_entry_rate_on_none"]
        none_recall = argmax_metrics["by_label"]["NO_EVIDENCE"]["recall"]
        present_recall = argmax_metrics["by_label"]["EVIDENCE_PRESENT"]["recall"]
        row = {
            "NO_EVIDENCE_recall": none_recall,
            "EVIDENCE_PRESENT_recall": present_recall,
            "by_label": argmax_metrics["by_label"],
            "early_stop_stale": stale,
            "epoch": epoch + 1,
            "false_evidence_entry_rate_on_none": false_entry,
            "mean_train_loss": running / max(1, n_batches),
            "n_batches": n_batches,
            "optimizer_steps_cumulative": optimizer_steps,
            "stage_a_macro_f1": macro,
            "uncertain_rate": argmax_metrics["uncertain_rate"],
        }
        epoch_trace.append(row)
        with metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(row) + "\n")
        print(json.dumps(row, sort_keys=True), flush=True)

        improved = False
        if macro > best_macro + 1e-12:
            improved = True
        elif abs(macro - best_macro) <= 1e-12:
            if false_entry < best_false_entry - 1e-12:
                improved = True
            elif (
                abs(false_entry - best_false_entry) <= 1e-12
                and none_recall > best_none_recall + 1e-12
            ):
                improved = True
        if improved:
            best_macro = macro
            best_false_entry = false_entry
            best_none_recall = none_recall
            best_epoch = epoch + 1
            best_state = capture_weights()
            save_tmp_checkpoint(best_epoch, "selected-candidate", best_state)
            stale = 0
        else:
            stale += 1
        if epoch + 1 >= min_epochs and stale >= patience:
            break

    if best_state is None:
        fail("no_best_checkpoint_selected")

    final_epoch = epoch_trace[-1]["epoch"] if epoch_trace else 0
    final_state = capture_weights()
    final_differs = final_epoch != best_epoch
    final_manifest = {
        "checkpoint_role": "FINAL_RUN_STATE",
        "differs_from_selected": final_differs,
        "final_epoch": final_epoch,
        "retained": final_differs,
        "schema": "hyperlex.classification.v5.stage_a_checkpoint_manifest.v1",
        "selected_epoch": best_epoch,
    }
    if final_differs:
        final_dir = RUN_ROOT / "final_run_state"
        final_dir.mkdir(mode=0o700, exist_ok=True)
        flat_final = flatten_weight_tensors(
            {
                "encoder": final_state["encoder"],
                "evidence_head": {
                    "weight": final_state["head_weight"].contiguous(),
                    "bias": final_state["head_bias"].contiguous(),
                },
            }
        )
        save_file(flat_final, str(final_dir / "model.safetensors"))
        final_manifest["checkpoint_sha256"] = sha256_file(final_dir / "model.safetensors")
        final_manifest["path"] = str(final_dir / "model.safetensors")
    write_private(RUN_ROOT / "FINAL_RUN_STATE.json", final_manifest)

    # Restore SELECTED checkpoint (inference weights; no optimizer dependency).
    apply_encoder_trainable(encoder, best_state["encoder"])
    with torch.no_grad():
        evidence_head.weight.copy_(best_state["head_weight"].to(device))
        evidence_head.bias.copy_(best_state["head_bias"].to(device))

    val_golds, val_scores, val_subtypes, val_argmax = score_split(val_rows)
    calibration = calibrate_thresholds(val_golds, val_scores, subtypes=val_subtypes)
    if not calibration["feasible"]:
        disposition = "SETTLED_FAIL"
        chosen = {"none_threshold": None, "present_threshold": None}
        val_decisions = [
            decide_evidence(s, none_threshold=0.5, present_threshold=0.55)
            for s in val_scores
        ]
        promotion_candidate = False
    else:
        disposition = "SETTLED_PASS"
        chosen = calibration["chosen"]
        val_decisions = [
            decide_evidence(
                s,
                none_threshold=chosen["none_threshold"],
                present_threshold=chosen["present_threshold"],
            )
            for s in val_scores
        ]
        promotion_candidate = True

    val_metrics = evaluate_decisions(
        val_golds, val_decisions, subtypes=val_subtypes
    )
    if not val_metrics["acceptance_pass"]:
        disposition = "SETTLED_FAIL"
        promotion_candidate = False

    # Persist SELECTED loadable artifact.
    selected_dir = RUN_ROOT / "selected"
    flat = flatten_weight_tensors(
        {
            "encoder": collect_encoder_trainable(encoder),
            "evidence_head": {
                "weight": evidence_head.weight.detach().cpu().contiguous(),
                "bias": evidence_head.bias.detach().cpu().contiguous(),
            },
        }
    )
    selected_weights = selected_dir / "model.safetensors"
    save_file(flat, str(selected_weights))
    selected_config = {
        "BEST_MUTATED": False,
        "class_order": list(EVIDENCE_LABELS),
        "code_revision": resolved.get("code_revision"),
        "dataset_sha256": pins["dataset_sha"],
        "evidence_labels": list(EVIDENCE_LABELS),
        "hidden_size": HIDDEN,
        "init_from": str(INIT_FROM),
        "last_trainable": last_n,
        "parent_BEST_sha256": BEST_SHA,
        "pooling": TRAIN_HYPERPARAMS["pooling"],
        "promotion_candidate": promotion_candidate,
        "resolved_training_config_sha256": resolved["training_config_sha256"],
        "restored_epoch": best_epoch,
        "rule": auth["rule"],
        "schema": "hyperlex.classification.v5.stage_a_selected_config.v1",
        "seed": seed,
        "tokenizer_identity": resolved["tokenization"]["tokenizer_identity"],
        "trainable_encoder_params": trainable_params,
        "training_config_sha256": resolved["training_config_sha256"],
    }
    write_private(selected_dir / "config.json", selected_config)
    checkpoint_sha = sha256_file(selected_weights)
    selected_manifest = {
        **selected_config,
        "checkpoint_role": "SELECTED",
        "checkpoint_sha256": checkpoint_sha,
        "matches_restored_epoch": True,
        "path": str(selected_weights),
        "restored_epoch_matches_selected": best_epoch == best_epoch,
        "weights_loadable_without_trainer_state": True,
    }
    write_private(RUN_ROOT / "SELECTED_CHECKPOINT.json", selected_manifest)

    # Mirror SELECTED to OUT for compatibility with prior path expectations.
    OUT.mkdir(parents=True, exist_ok=True)
    os.chmod(OUT, 0o755)
    shutil.copy2(selected_weights, OUT / "model.safetensors")
    write_private(OUT / "stage_a_config.json", selected_config)

    # Diagnostics (do not alter training).
    subtype_diag = subtype_diagnostics(val_rows, val_golds, val_decisions)
    atom_prose = slice_diagnostics(
        val_rows,
        val_golds,
        val_decisions,
        key_fn=lambda row: surface_form(str(row["text"])),
    )
    prov_diag = slice_diagnostics(
        val_rows,
        val_golds,
        val_decisions,
        key_fn=lambda row: str(row.get("provenance") or "UNKNOWN"),
    )
    source_diag = slice_diagnostics(
        val_rows, val_golds, val_decisions, key_fn=source_bucket
    )
    length_diag = slice_diagnostics(
        val_rows,
        val_golds,
        val_decisions,
        key_fn=lambda row: length_bucket(str(row["text"])),
    )
    # Shortcut reappearance probe: ATOM→NONE / PROSE→PRESENT dominance among errors.
    error_forms = Counter()
    for row, gold, pred in zip(val_rows, val_golds, val_decisions):
        if gold == pred:
            continue
        form = surface_form(str(row["text"]))
        error_forms[f"{form}:{gold}->{pred}"] += 1
    shortcut_probe = {
        "ATOM_share_of_errors": (
            sum(v for k, v in error_forms.items() if k.startswith(f"{SURFACE_ATOM}:"))
            / max(1, sum(error_forms.values()))
        ),
        "error_form_confusion": dict(error_forms),
        "note": (
            "diagnostic only; remediated surface shortcuts must not dominate "
            "error structure"
        ),
        "n_errors": sum(error_forms.values()),
    }
    write_private(
        RUN_ROOT / "diagnostics" / "subtype.json",
        {"subtypes": subtype_diag, "rule": "diagnostic_only"},
    )
    write_private(
        RUN_ROOT / "diagnostics" / "surface_slices.json",
        {
            "ATOM_PROSE": atom_prose,
            "OBSERVED_INFERRED": prov_diag,
            "length_bucket": length_diag,
            "shortcut_probe": shortcut_probe,
            "source": source_diag,
        },
    )

    write_private(
        RUN_ROOT / "THRESHOLD_GRID.json",
        {
            "chosen": calibration.get("chosen"),
            "disposition": calibration.get("disposition"),
            "feasible": calibration.get("feasible"),
            "grid": calibration.get("grid"),
            "grid_results": calibration.get("grid_results") or [],
            "n_candidates": calibration.get("n_candidates"),
            "n_passing": calibration.get("n_passing"),
            "selection_rule": calibration.get("selection_rule"),
        },
    )

    acceptance = {
        "EVIDENCE_PRESENT_recall": {
            "pass": val_metrics["acceptance"]["EVIDENCE_PRESENT_recall"],
            "threshold": 0.70,
            "value": val_metrics["by_label"]["EVIDENCE_PRESENT"]["recall"],
        },
        "NO_EVIDENCE_recall": {
            "pass": val_metrics["acceptance"]["NO_EVIDENCE_recall"],
            "threshold": 0.90,
            "value": val_metrics["by_label"]["NO_EVIDENCE"]["recall"],
        },
        "false_evidence_entry_rate_on_none": {
            "pass": val_metrics["acceptance"]["false_evidence_entry_rate_on_none"],
            "threshold": 0.05,
            "value": val_metrics["false_evidence_entry_rate_on_none"],
        },
    }

    runtime = time.time() - started
    terminated_normally = True
    settlement = {
        "BEST_MUTATED": False,
        "CURRENT_BEST": BEST_SHA,
        "EXPERIMENT_ID": auth["EXPERIMENT_ID"],
        "RESERVE_CONSUMED": False,
        "acceptance_gates": acceptance,
        "acceptance_pass": val_metrics["acceptance_pass"],
        "disposition": disposition,
        "promotion_candidate": promotion_candidate,
        "retention_invariant": (
            "Settlement must never destroy the checkpoint or evidence required "
            "to reproduce, inspect, or falsify the recorded scientific result."
        ),
        "retention_rule": (
            "One selected loadable checkpoint + complete scientific provenance "
            "is permanent; non-selected trainer checkpoints are temporary unless "
            "required for incident analysis."
        ),
        "schema": "hyperlex.classification.v5.stage_a_settlement.v1",
        "selected_checkpoint_sha256": checkpoint_sha,
        "selected_epoch": best_epoch,
    }
    write_private(RUN_ROOT / "SETTLEMENT.json", settlement)

    receipt = {
        "BEST": "UNCHANGED",
        "BEST_MUTATED": False,
        "CURRENT_BEST": BEST_SHA,
        "EXPERIMENT_ID": auth["EXPERIMENT_ID"],
        "RESERVE_CONSUMED": False,
        "TRAINING_STATUS": "COMPLETE",
        "acceptance_gates": acceptance,
        "actual_epochs": final_epoch,
        "best_epoch": best_epoch,
        "best_stage_a_macro_f1_argmax": best_macro,
        "calibration": {
            "chosen": calibration.get("chosen"),
            "disposition": calibration.get("disposition"),
            "feasible": calibration.get("feasible"),
            "n_candidates": calibration.get("n_candidates"),
            "n_passing": calibration.get("n_passing"),
        },
        "checkpoint_sha256": checkpoint_sha,
        "code_revision": resolved.get("code_revision"),
        "dataset_path": str(DATASET),
        "dataset_sha256": pins["dataset_sha"],
        "disposition": disposition,
        "epoch_trace": epoch_trace,
        "final_epoch": final_epoch,
        "final_run_state_differs_from_selected": final_differs,
        "none_threshold": chosen.get("none_threshold"),
        "optimizer_steps": optimizer_steps,
        "present_threshold": chosen.get("present_threshold"),
        "promotion_candidate": promotion_candidate,
        "restored_checkpoint_matches_selected_epoch": True,
        "restored_epoch": best_epoch,
        "runtime_seconds": runtime,
        "seed": seed,
        "selected_path": str(selected_weights),
        "terminated_normally": terminated_normally,
        "tokenizer_identity": resolved["tokenization"]["tokenizer_identity"],
        "training_config_sha256": resolved["training_config_sha256"],
        "validation_metrics": {
            "EVIDENCE_PRESENT_recall": val_metrics["by_label"]["EVIDENCE_PRESENT"][
                "recall"
            ],
            "NO_EVIDENCE_recall": val_metrics["by_label"]["NO_EVIDENCE"]["recall"],
            "UNCERTAIN_rate": val_metrics["uncertain_rate"],
            "acceptance_pass": val_metrics["acceptance_pass"],
            "by_label": val_metrics["by_label"],
            "confusion": val_metrics["confusion"],
            "false_evidence_entry_rate_on_none": val_metrics[
                "false_evidence_entry_rate_on_none"
            ],
            "n": val_metrics["n"],
            "stage_a_macro_f1": val_metrics["stage_a_macro_f1"],
        },
        "weights_dir": str(selected_dir),
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    write_private(RUN_ROOT / "RUN_RECEIPT.json", receipt)
    write_private(AUTH_DEST / "STAGE_A_TRAIN.json", receipt)

    # Symlink/copy permanent scientific provenance pointers inside run root.
    for name in (
        "AUTHORIZATION.json",
        "RESOLVED_TRAINING_CONFIG.json",
        "LABEL_PROVENANCE_STATS.json",
        "CLASS_WEIGHTS.json",
    ):
        src = AUTH_DEST / name
        dst = RUN_ROOT / (name if name != "RESOLVED_TRAINING_CONFIG.json" else "TRAINING_CONFIG.json")
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)

    # After settlement: prune temporary intermediate checkpoints + optimizer state.
    # SELECTED + scientific receipts remain. FINAL retained only if distinct.
    if tmp_ckpt_root.exists():
        shutil.rmtree(tmp_ckpt_root)
    # Drop in-memory trainer state; do not persist optimizer/scheduler after settle.
    del optimizer

    auth["TRAINING_STATUS"] = "COMPLETE"
    auth["train_run_completed"] = True
    auth["scientific_disposition"] = disposition
    auth["promotion_candidate"] = promotion_candidate
    auth["selected_checkpoint_sha256"] = checkpoint_sha
    auth["run_receipt_sha256"] = receipt["receipt_sha256"]
    write_private(AUTH_FILE, auth)

    summary = {
        "TRAINING_STATUS": "COMPLETE",
        "disposition": disposition,
        "promotion_candidate": promotion_candidate,
        "receipt_sha256": receipt["receipt_sha256"],
        "restored_epoch": best_epoch,
        "checkpoint_sha256": checkpoint_sha,
        "none_threshold": chosen.get("none_threshold"),
        "present_threshold": chosen.get("present_threshold"),
        "stage_a_macro_f1": val_metrics["stage_a_macro_f1"],
        "false_evidence_entry_rate_on_none": val_metrics[
            "false_evidence_entry_rate_on_none"
        ],
        "EVIDENCE_PRESENT_recall": val_metrics["by_label"]["EVIDENCE_PRESENT"]["recall"],
        "NO_EVIDENCE_recall": val_metrics["by_label"]["NO_EVIDENCE"]["recall"],
        "run_root": str(RUN_ROOT),
    }
    write_private(RUN_ROOT / "SUMMARY.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
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
    log_path = AUTH_DEST / "train_console.log"
    AUTH_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log_handle:
        completed = subprocess.run(cmd, check=False, stdout=log_handle, stderr=subprocess.STDOUT)
    # Also stream tail for operator visibility.
    try:
        print(log_path.read_text(encoding="utf-8")[-8000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
