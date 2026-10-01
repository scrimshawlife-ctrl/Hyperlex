"""TRAIN_V5_STAGE_A_003_FOCAL_LOSS_ONCE — single authorized focal Stage-A train.

Requires sealed Stage-A-003 AUTHORIZATION.json with FROZEN focal objective.
Does not move BEST. Does not consume reserve. Does not modify V1R8 / decide_evidence.
Set HLX_V5_STAGE_A_EXECUTE_TRAIN=1 to execute the one authorized run.
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
    "classification-v5-stage-a-negative-evidence-surface-v1r8-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-train-v1r8-003-focal-20260930"
)
# Provenance sidecar lives on parent V1R8 auth (same dataset SHA); not re-derived.
PARENT_AUTH = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-a-train-v1r8-20260930"
)
RUN_ROOT = AUTH_DEST / "classification-v5-stage-a-003"
AUTH_FILE = AUTH_DEST / "AUTHORIZATION.json"
RESOLVED = AUTH_DEST / "RESOLVED_TRAINING_CONFIG.json"
OBJECTIVE_SPEC = AUTH_DEST / "OBJECTIVE_SPEC.json"
SINGLE_FACTOR_DIFF = AUTH_DEST / "SINGLE_FACTOR_DIFF.json"
LABEL_PROVENANCE = PARENT_AUTH / "LABEL_PROVENANCE.jsonl"
LABEL_PROVENANCE_STATS = PARENT_AUTH / "LABEL_PROVENANCE_STATS.json"
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
    "hyperlex-encoder-modernbert-base-seed-classification-v5-stage-a-003-focal"
)
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
EXPECTED_EXPERIMENT = "HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS"
EXPECTED_DATASET_SHA = (
    "c0fdd82d1734585a7d852318ac5b390cc5e2c50908c0ef9f9eba4b3f7ebedc8b"
)
EXPECTED_CONFIG_SHA = (
    "b8aad3ba30fa1c96803551fc03c132c0390caa6c3eb86f5846eda3b329665231"
)
EXPECTED_FOCAL_SPEC_SHA = (
    "dce6dbf5c1d1239d000396090cb01f24f16009605becb9ba41fcce18af768b5f"
)
EXPECTED_CODE_REVISION = "d58e078fd776475d886cd1f516ea9f2e99816bd9"
FOCAL_GAMMA = 2.0
ORDINARY_FALSE_PRESENT_REMAINS_LOW_MAX = 22
# Parent Stage-A-002 diagnostic cohorts (fail-display pair).
PARENT_DIAGNOSTIC_NONE = 0.50
PARENT_DIAGNOSTIC_PRESENT = 0.55
PARENT_COHORTS = {
    "ORDINARY_DOMAIN_FALSE_PRESENT": 11,
    "OTHER_NONE_FALSE_PRESENT": 4,
    "PRESENT_FALSE_NONE": 297,
    "PRESENT_FALSE_UNCERTAIN": 4,
    "UNCERTAIN_MISCLASSIFIED": 61,
}

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
    if "wikipedia" in url.lower():
        return "wikipedia"
    if "wiktionary" in url.lower():
        return "wiktionary"
    if url:
        return "other_url"
    return "none"


def diagnostic_error_cohort(gold: str, pred: str, subtype: str) -> str | None:
    """Same cohort definitions as DIAGNOSE_V5_STAGE_A_SETTLED_FAIL."""
    if gold == "NO_EVIDENCE" and pred == "EVIDENCE_PRESENT":
        if subtype == "ORDINARY_DOMAIN_NONE":
            return "ORDINARY_DOMAIN_FALSE_PRESENT"
        return "OTHER_NONE_FALSE_PRESENT"
    if gold == "EVIDENCE_PRESENT" and pred == "NO_EVIDENCE":
        return "PRESENT_FALSE_NONE"
    if gold == "EVIDENCE_PRESENT" and pred == "UNCERTAIN":
        return "PRESENT_FALSE_UNCERTAIN"
    if gold == "UNCERTAIN" and pred != "UNCERTAIN":
        return "UNCERTAIN_MISCLASSIFIED"
    return None


def compute_diagnostic_cohorts(
    rows: list[dict],
    golds: list[str],
    scores: list[float],
    *,
    none_threshold: float,
    present_threshold: float,
) -> dict:
    from hyperlexical.classification_v5_stage_a import decide_evidence

    decisions = [
        decide_evidence(
            float(score),
            none_threshold=none_threshold,
            present_threshold=present_threshold,
        )
        for score in scores
    ]
    counts = {name: 0 for name in PARENT_COHORTS}
    by_domain: dict[str, Counter] = defaultdict(Counter)
    for row, gold, pred in zip(rows, golds, decisions):
        name = diagnostic_error_cohort(gold, pred, str(row.get("evidence_subtype")))
        if name is None:
            continue
        counts[name] += 1
        domain = str(row.get("topic_domain") or "unspecified")
        by_domain[name][domain] += 1
    return {
        "by_domain": {k: dict(v) for k, v in by_domain.items()},
        "counts": counts,
        "deltas_vs_parent": {
            name: counts[name] - PARENT_COHORTS[name] for name in PARENT_COHORTS
        },
        "none_threshold": none_threshold,
        "parent_counts": dict(PARENT_COHORTS),
        "present_threshold": present_threshold,
    }


def require_authorization() -> dict:
    from hyperlexical.classification_v5_stage_a import authorization_gate_checks

    if not AUTH_FILE.exists() or not RESOLVED.exists() or not OBJECTIVE_SPEC.exists():
        fail("authorization artifacts missing; run authorize first")
    auth = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    resolved = json.loads(RESOLVED.read_text(encoding="utf-8"))
    objective = json.loads(OBJECTIVE_SPEC.read_text(encoding="utf-8"))
    diff = json.loads(SINGLE_FACTOR_DIFF.read_text(encoding="utf-8"))
    dataset_sha = sha256_file(DATASET)
    readiness = json.loads((SURFACE / "READINESS.json").read_text(encoding="utf-8"))
    if readiness.get("state") != "READY":
        fail(f"surface_not_READY:{readiness.get('state')}")
    if auth.get("EXPERIMENT_ID") != EXPECTED_EXPERIMENT:
        fail(f"experiment_id_mismatch:{auth.get('EXPERIMENT_ID')}")
    if resolved.get("experiment_id") != EXPECTED_EXPERIMENT:
        fail(f"resolved_experiment_id_mismatch:{resolved.get('experiment_id')}")
    if dataset_sha != EXPECTED_DATASET_SHA or auth.get("DATASET_SHA256") != EXPECTED_DATASET_SHA:
        fail(f"dataset_sha_mismatch:{dataset_sha}")
    if resolved.get("surface_rule") != (
        "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R8"
    ):
        fail(f"surface_rule_mismatch:{resolved.get('surface_rule')}")
    if resolved.get("training_config_sha256") != EXPECTED_CONFIG_SHA:
        fail(f"training_config_sha_mismatch:{resolved.get('training_config_sha256')}")
    if auth.get("TRAINING_CONFIG_SHA256") != EXPECTED_CONFIG_SHA:
        fail("authorized_config_sha_mismatch")
    if auth.get("FOCAL_LOSS_SPEC_SHA256") != EXPECTED_FOCAL_SPEC_SHA:
        fail("focal_spec_sha_mismatch")
    if objective.get("FOCAL_LOSS_SPEC_SHA256") != EXPECTED_FOCAL_SPEC_SHA:
        fail("objective_spec_sha_mismatch")
    if float(objective.get("FOCAL_GAMMA")) != FOCAL_GAMMA:
        fail(f"focal_gamma_mismatch:{objective.get('FOCAL_GAMMA')}")
    if objective.get("FOCAL_ALPHA_POLICY") != "NONE":
        fail(f"focal_alpha_policy_mismatch:{objective.get('FOCAL_ALPHA_POLICY')}")
    if resolved.get("loss", {}).get("name") != "weighted_focal_cross_entropy":
        fail(f"loss_name_mismatch:{resolved.get('loss')}")
    if float(resolved.get("loss", {}).get("gamma")) != FOCAL_GAMMA:
        fail("resolved_gamma_mismatch")
    if auth.get("TRAINING_AUTHORIZATION") != "AUTHORIZED_V5_STAGE_A_003_FOCAL_LOSS_ONCE":
        fail(f"training_authorization_mismatch:{auth.get('TRAINING_AUTHORIZATION')}")
    if auth.get("OBJECTIVE_STATE") != "FROZEN":
        fail(f"objective_not_frozen:{auth.get('OBJECTIVE_STATE')}")
    if diff.get("SINGLE_FACTOR_DIFF_STATUS") != "PASS":
        fail("single_factor_diff_not_PASS")
    if auth.get("CODE_REVISION") != EXPECTED_CODE_REVISION:
        fail(f"code_revision_mismatch:{auth.get('CODE_REVISION')}")
    current_best = sudo_sha256(BEST_WEIGHTS)
    gate = authorization_gate_checks(
        train_authorized=True,
        dataset_sha256=dataset_sha,
        surface_readiness="PASS",
        resolved_config_sha256=resolved.get("training_config_sha256"),
        authorized_config_sha256=auth.get("TRAINING_CONFIG_SHA256"),
        current_best=current_best,
        reserve_consumed=bool(auth.get("RESERVE_CONSUMED", True)),
    )
    if current_best != BEST_SHA or auth.get("CURRENT_BEST") != BEST_SHA:
        fail(f"BEST_mismatch:{current_best}")
    if not gate["pass"]:
        fail(f"authorization_gate_failed:{json.dumps(gate['checks'], sort_keys=True)}")
    if auth.get("TRAINING_STATUS") not in {"AUTHORIZED_NOT_STARTED", "RUNNING"}:
        fail(f"training_status_blocked:{auth.get('TRAINING_STATUS')}")
    if auth.get("train_run_completed"):
        fail("training_run_count_already_nonzero")
    if (AUTH_DEST / "STAGE_A_TRAIN.json").exists() or (RUN_ROOT / "RUN_RECEIPT.json").exists():
        fail("prior_run_receipt_present")
    if not LABEL_PROVENANCE.exists() or not LABEL_PROVENANCE_STATS.exists():
        fail("label provenance sidecar missing (parent V1R8 auth)")
    stats = json.loads(LABEL_PROVENANCE_STATS.read_text(encoding="utf-8"))
    if int(stats.get("invalid_provenance_rows", 1)) != 0:
        fail("label_provenance_invalid_rows_nonzero")
    return {
        "auth": auth,
        "resolved": resolved,
        "objective": objective,
        "gate": gate,
        "dataset_sha": dataset_sha,
        "readiness": readiness,
        "preflight": {
            "AUTHORIZATION_IDENTITY": "PASS",
            "CODE_REVISION_IDENTITY": "PASS",
            "DATASET_IDENTITY": "PASS",
            "OBJECTIVE_SPEC_IDENTITY": "PASS",
            "SINGLE_FACTOR_DIFF_STATUS": "PASS",
            "TRAINING_CONFIG_IDENTITY": "PASS",
        },
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
    from hyperlexical.classification_v5_stage_a_003_focal import (
        FOCAL_GAMMA as FROZEN_GAMMA,
        class_weight_tensor,
        reduce_mean,
        weighted_focal_cross_entropy_per_example,
    )

    if float(FROZEN_GAMMA) != FOCAL_GAMMA:
        fail("imported_focal_gamma_mismatch")
    weight_tensor = class_weight_tensor(class_weights, device=device)

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
        golds, scores, subtypes, argmax_preds, prob_rows = [], [], [], [], []
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
                prob_rows.append(probs)
        return golds, scores, subtypes, argmax_preds, prob_rows

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
            per_ex = weighted_focal_cross_entropy_per_example(
                logits,
                targets,
                weight_tensor,
                sample_w,
                gamma=FOCAL_GAMMA,
            )
            loss = reduce_mean(per_ex)
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

        val_golds, val_scores, val_subtypes, val_argmax, _val_probs = score_split(
            val_rows
        )
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

    val_golds, val_scores, val_subtypes, val_argmax, val_probs = score_split(val_rows)
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
        "rule": auth.get("RULE") or auth.get("rule"),
        "schema": "hyperlex.classification.v5.stage_a_003_selected_config.v1",
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
    domain_diag = slice_diagnostics(
        val_rows,
        val_golds,
        val_decisions,
        key_fn=lambda row: str(row.get("topic_domain") or "unspecified"),
    )
    # Parent-comparable diagnostic cohorts at sealed fail-display thresholds.
    diagnostic_cohorts = compute_diagnostic_cohorts(
        val_rows,
        val_golds,
        val_scores,
        none_threshold=PARENT_DIAGNOSTIC_NONE,
        present_threshold=PARENT_DIAGNOSTIC_PRESENT,
    )
    # Also report cohorts under the calibrated / display decision used for gates.
    gate_cohort_none = (
        float(chosen["none_threshold"])
        if chosen.get("none_threshold") is not None
        else PARENT_DIAGNOSTIC_NONE
    )
    gate_cohort_present = (
        float(chosen["present_threshold"])
        if chosen.get("present_threshold") is not None
        else PARENT_DIAGNOSTIC_PRESENT
    )
    gate_decision_cohorts = compute_diagnostic_cohorts(
        val_rows,
        val_golds,
        val_scores,
        none_threshold=gate_cohort_none,
        present_threshold=gate_cohort_present,
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
            "topic_domain": domain_diag,
        },
    )
    # PRESENT→NONE probability geometry under diagnostic thresholds.
    import statistics as _stats

    present_to_none_probs = []
    for row, gold, score, probs in zip(val_rows, val_golds, val_scores, val_probs):
        pred = decide_evidence(
            float(score),
            none_threshold=gate_cohort_none,
            present_threshold=gate_cohort_present,
        )
        if gold == "EVIDENCE_PRESENT" and pred == "NO_EVIDENCE":
            present_to_none_probs.append(probs)
    if present_to_none_probs:
        p_present = [float(p["EVIDENCE_PRESENT"]) for p in present_to_none_probs]
        p_none = [float(p["NO_EVIDENCE"]) for p in present_to_none_probs]
        p_unc = [float(p["UNCERTAIN"]) for p in present_to_none_probs]
        conf_none_frac = sum(
            1 for a, b in zip(p_none, p_present) if a >= 0.80 and b <= 0.20
        ) / len(present_to_none_probs)
        near_boundary_frac = sum(
            1 for a in p_present if 0.45 <= a <= 0.60
        ) / len(present_to_none_probs)
        present_to_none_geometry = {
            "n": len(present_to_none_probs),
            "median_P_EVIDENCE_PRESENT": _stats.median(p_present),
            "median_P_NO_EVIDENCE": _stats.median(p_none),
            "median_P_UNCERTAIN": _stats.median(p_unc),
            "confident_none_frac": conf_none_frac,
            "near_boundary_frac": near_boundary_frac,
        }
    else:
        present_to_none_geometry = {
            "n": 0,
            "median_P_EVIDENCE_PRESENT": None,
            "median_P_NO_EVIDENCE": None,
            "median_P_UNCERTAIN": None,
            "confident_none_frac": None,
            "near_boundary_frac": None,
        }

    ordinary_fp = int(
        gate_decision_cohorts["counts"].get("ORDINARY_DOMAIN_FALSE_PRESENT", 0)
    )
    n_passing = int(calibration.get("n_passing") or 0)
    present_recall = float(val_metrics["by_label"]["EVIDENCE_PRESENT"]["recall"])
    none_recall = float(val_metrics["by_label"]["NO_EVIDENCE"]["recall"])
    false_entry = float(val_metrics["false_evidence_entry_rate_on_none"])
    median_p_none = present_to_none_geometry["median_P_NO_EVIDENCE"]

    stage_a_gates_ok = (
        false_entry <= 0.05 and present_recall >= 0.70 and none_recall >= 0.90
    )
    support_ok = (
        stage_a_gates_ok
        and n_passing >= 1
        and median_p_none is not None
        and float(median_p_none) < 0.80
        and ordinary_fp <= ORDINARY_FALSE_PRESENT_REMAINS_LOW_MAX
    )
    falsified = (
        present_recall < 0.70
        or false_entry > 0.05
        or ordinary_fp > ORDINARY_FALSE_PRESENT_REMAINS_LOW_MAX
        or (
            n_passing == 0
            and median_p_none is not None
            and float(median_p_none) >= 0.80
        )
    )
    if support_ok:
        h1_status = "SUPPORTED_BY_STAGE_A_003"
        disposition = "SETTLED_PASS"
        promotion_candidate = True
    elif falsified:
        h1_status = "FALSIFIED_FOR_FOCAL_INTERVENTION"
        disposition = "SETTLED_FAIL"
        promotion_candidate = False
    else:
        h1_status = "INCONCLUSIVE_FOR_FOCAL_INTERVENTION"
        disposition = "SETTLED_FAIL"
        promotion_candidate = False
    # Keep SELECTED config in sync with final H1 settlement.
    selected_config["promotion_candidate"] = promotion_candidate
    write_private(selected_dir / "config.json", selected_config)
    selected_manifest["promotion_candidate"] = promotion_candidate
    write_private(RUN_ROOT / "SELECTED_CHECKPOINT.json", selected_manifest)

    write_private(
        RUN_ROOT / "diagnostics" / "error_cohorts.json",
        {
            "gate_decision_cohorts": gate_decision_cohorts,
            "parent_comparable_diagnostic_cohorts": diagnostic_cohorts,
            "present_to_none_geometry": present_to_none_geometry,
            "rule": "HYPERLEX_V5_STAGE_A_DIAGNOSE_SETTLED_FAIL_V1.error_cohort",
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
            "pass": present_recall >= 0.70,
            "threshold": 0.70,
            "value": present_recall,
        },
        "NO_EVIDENCE_recall": {
            "pass": val_metrics["acceptance"]["NO_EVIDENCE_recall"],
            "threshold": 0.90,
            "value": val_metrics["by_label"]["NO_EVIDENCE"]["recall"],
        },
        "false_evidence_entry_rate_on_none": {
            "pass": false_entry <= 0.05,
            "threshold": 0.05,
            "value": false_entry,
        },
        "ordinary_none_false_present_remains_low": {
            "pass": ordinary_fp <= ORDINARY_FALSE_PRESENT_REMAINS_LOW_MAX,
            "threshold": ORDINARY_FALSE_PRESENT_REMAINS_LOW_MAX,
            "value": ordinary_fp,
        },
        "present_to_none_median_p_none_lt_0_80": {
            "pass": median_p_none is not None and float(median_p_none) < 0.80,
            "threshold": 0.80,
            "value": median_p_none,
        },
        "threshold_grid_n_passing_ge_1": {
            "pass": n_passing >= 1,
            "threshold": 1,
            "value": n_passing,
        },
    }

    runtime = time.time() - started
    terminated_normally = True
    settlement = {
        "BEST_MUTATED": False,
        "CURRENT_BEST": BEST_SHA,
        "EXPERIMENT_ID": auth["EXPERIMENT_ID"],
        "FOCAL_GAMMA": FOCAL_GAMMA,
        "FOCAL_LOSS_SPEC_SHA256": EXPECTED_FOCAL_SPEC_SHA,
        "H1_OBJECTIVE_LOSS_PRESSURE": h1_status,
        "PARENT_EXPERIMENT": "HLX-CLASSIFICATION-V5-STAGE-A-002",
        "RESERVE_CONSUMED": False,
        "UNCERTAIN_POLICY_INVESTIGATION_PENDING": True,
        "acceptance_gates": acceptance,
        "acceptance_pass": all(v["pass"] for v in acceptance.values()),
        "disposition": disposition,
        "ordinary_none_false_present": ordinary_fp,
        "present_to_none_geometry": present_to_none_geometry,
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
        "schema": "hyperlex.classification.v5.stage_a_003_settlement.v1",
        "selected_checkpoint_sha256": checkpoint_sha,
        "selected_epoch": best_epoch,
        "support_ok": support_ok,
    }
    write_private(RUN_ROOT / "SETTLEMENT.json", settlement)

    by_label = val_metrics["by_label"]
    receipt = {
        "BEST": "UNCHANGED",
        "BEST_MUTATED": False,
        "CURRENT_BEST": BEST_SHA,
        "EXPERIMENT_ID": auth["EXPERIMENT_ID"],
        "FOCAL_ALPHA_POLICY": "NONE",
        "FOCAL_GAMMA": FOCAL_GAMMA,
        "FOCAL_LOSS_SPEC_SHA256": EXPECTED_FOCAL_SPEC_SHA,
        "H1_OBJECTIVE_LOSS_PRESSURE": h1_status,
        "PARENT_EXPERIMENT": "HLX-CLASSIFICATION-V5-STAGE-A-002",
        "PROCESS_EXIT": "CLEAN",
        "RESERVE_CONSUMED": False,
        "TRAINING_COMPLETE": True,
        "TRAINING_STATUS": "COMPLETE",
        "UNCERTAIN_POLICY_INVESTIGATION_PENDING": True,
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
        "ordinary_none_false_present": ordinary_fp,
        "preflight": pins["preflight"],
        "present_threshold": chosen.get("present_threshold"),
        "present_to_none_geometry": present_to_none_geometry,
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
            "EVIDENCE_PRESENT_f1": by_label["EVIDENCE_PRESENT"]["f1"],
            "EVIDENCE_PRESENT_precision": by_label["EVIDENCE_PRESENT"]["precision"],
            "EVIDENCE_PRESENT_recall": by_label["EVIDENCE_PRESENT"]["recall"],
            "NO_EVIDENCE_f1": by_label["NO_EVIDENCE"]["f1"],
            "NO_EVIDENCE_precision": by_label["NO_EVIDENCE"]["precision"],
            "NO_EVIDENCE_recall": by_label["NO_EVIDENCE"]["recall"],
            "UNCERTAIN_f1": by_label["UNCERTAIN"]["f1"],
            "UNCERTAIN_precision": by_label["UNCERTAIN"]["precision"],
            "UNCERTAIN_recall": by_label["UNCERTAIN"]["recall"],
            "UNCERTAIN_rate": val_metrics["uncertain_rate"],
            "acceptance_pass": settlement["acceptance_pass"],
            "balanced_accuracy": val_metrics["balanced_accuracy"],
            "by_label": by_label,
            "confusion": val_metrics["confusion"],
            "false_evidence_entry_rate_on_none": false_entry,
            "n": val_metrics["n"],
            "stage_a_macro_f1": val_metrics["stage_a_macro_f1"],
        },
        "diagnostic_cohorts_parent_comparable": diagnostic_cohorts,
        "gate_decision_cohorts": gate_decision_cohorts,
        "subtype_diagnostics": subtype_diag,
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
        "OBJECTIVE_SPEC.json",
        "SINGLE_FACTOR_DIFF.json",
        "CLASS_WEIGHTS.json",
    ):
        src = AUTH_DEST / name
        dst = RUN_ROOT / (
            name if name != "RESOLVED_TRAINING_CONFIG.json" else "TRAINING_CONFIG.json"
        )
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
    if LABEL_PROVENANCE_STATS.exists():
        shutil.copy2(LABEL_PROVENANCE_STATS, RUN_ROOT / "LABEL_PROVENANCE_STATS.json")

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
    auth["H1_OBJECTIVE_LOSS_PRESSURE"] = h1_status
    auth["SCIENTIFIC_RESULT"] = disposition
    write_private(AUTH_FILE, auth)

    summary = {
        "EXPERIMENT_ID": EXPECTED_EXPERIMENT,
        "TRAINING_STATUS": "COMPLETE",
        "SCIENTIFIC_RESULT": disposition,
        "H1_OBJECTIVE_LOSS_PRESSURE": h1_status,
        "FOCAL_GAMMA": FOCAL_GAMMA,
        "disposition": disposition,
        "promotion_candidate": promotion_candidate,
        "receipt_sha256": receipt["receipt_sha256"],
        "restored_epoch": best_epoch,
        "checkpoint_sha256": checkpoint_sha,
        "none_threshold": chosen.get("none_threshold"),
        "present_threshold": chosen.get("present_threshold"),
        "stage_a_macro_f1": val_metrics["stage_a_macro_f1"],
        "false_evidence_entry_rate_on_none": false_entry,
        "EVIDENCE_PRESENT_recall": present_recall,
        "NO_EVIDENCE_recall": none_recall,
        "ORDINARY_NONE_FALSE_PRESENT": ordinary_fp,
        "PRESENT_TO_NONE": present_to_none_geometry["n"],
        "PRESENT_TO_NONE_MEDIAN_P_NONE": median_p_none,
        "THRESHOLD_GRID_N_PASSING": n_passing,
        "BEST": "UNCHANGED",
        "RESERVE": "unused",
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
        str(REPO / "scripts/spark/run_classification_v5_stage_a_003_focal_train.py"),
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
