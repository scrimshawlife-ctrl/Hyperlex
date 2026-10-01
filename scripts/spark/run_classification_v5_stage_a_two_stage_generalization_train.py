"""TRAIN_V5_STAGE_A_TWO_STAGE_GENERALIZATION_ONCE — V1R1 fresh two-stage retrain.

Requires sealed AUTHORIZE_V5_STAGE_A_TWO_STAGE_RETRAIN_ON_GENERALIZATION_SURFACE.
Consumes sealed V1R1 literal class weights; does not recompute.
Fresh init from MODEL_WIDE_BEST (not STAGE_A_BEST continuation).
Does not move BEST/STAGE_A_BEST. Does not touch spent reserve. Does not alter V1R1.

Set HLX_V5_STAGE_A_EXECUTE_GENERALIZATION_TRAIN=1 to execute the one authorized run.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-generalization-surface-v1r1-20261001"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "4095036e5af3ad7cfe9f038dd3e1f46e4ef0ea18db4c4b7186fc2b02e96d4274"
ARCHITECTURE_RECEIPT_SHA = (
    "631427cc4c1b09bac1e3a2c5e081c7e9fc0947babda26c03cb73895f47754697"
)
AUTHORIZED_CONFIG_SHA = (
    "1527ae1887b362f4e659409fcf3e4c15f0d2b410c8157759c5a12c1372166e31"
)
AUTHORIZED_WEIGHT_SHA = (
    "80b7f8991ec14b39223e232fad3a4590d54548f9fcd68cc9c70e9884f7aba5a4"
)
AUTHORIZED_AUTH_SHA = (
    "f7d4f3ad03dd4d13ea34dfb380451840e29f5e82e924eccfbe96532f865e8f2f"
)
AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-two-stage-generalization-train-v1-20261001"
)
AUTH_FILE = AUTH_DEST / "AUTHORIZATION.json"
RESOLVED = AUTH_DEST / "RESOLVED_TRAINING_CONFIG.json"
WEIGHTS = AUTH_DEST / "V1R1_TWO_STAGE_CLASS_WEIGHTS.json"
RUN_ROOT = AUTH_DEST / "classification-v5-stage-a-two-stage-generalization-001"
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
    "hyperlex-encoder-modernbert-base-seed-classification-v5-stage-a-two-stage-generalization-001"
)
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001"
)
SPEC_DIR = REPO / "specs" / "007-hyperlexical-model"

LITERAL_G1 = {
    "NO_EVIDENCE": 1.0006485087033488,
    "POSSIBLE_EVIDENCE": 0.9993514912966515,
}
LITERAL_G2 = {
    "UNCERTAIN": 1.375376244120633,
    "CONFIRMED_PRESENT": 0.6246237558793669,
}
READINESS_SHA = "c4b5fc0725b919c1dd11acfd575d594d8ddd76839836e5a3928f4d6c07030c96"
SURFACE_RECEIPT_SHA = (
    "3dbdd9b2cc30600698340f979d20a2c9b8559b9eafbbc24baf4fb1007e737fb9"
)
STAGE_A_BEST_SHA = (
    "cd2829c1b5fb823fc03f18efe66a7387124ef44be2545b9e385a17eb6237bf5c"
)
DISJOINTNESS = SURFACE / "DISJOINTNESS_WITNESS.json"

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


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def source_bucket(row: dict) -> str:
    url = str(row.get("source_url") or "")
    if "wikipedia" in url.lower():
        return "wikipedia"
    if "wiktionary" in url.lower():
        return "wiktionary"
    bucket = str(row.get("source_bucket") or "")
    if bucket:
        return bucket
    if url:
        return "other_url"
    return "none"


def require_authorization() -> dict:
    from hyperlexical.classification_v5_stage_a_gold_label_mapping import (
        admission_invariants,
    )
    from hyperlexical.classification_v5_stage_a_two_stage import (
        ARCHITECTURE_RECEIPT_SHA256,
        identity_list_sha256,
    )
    from hyperlexical.classification_v5_stage_a_two_stage_generalization import (
        AUTHORIZE_RULE,
        AUTHORIZED_AUTH_RECEIPT_SHA256,
        AUTHORIZED_BEST_SHA,
        AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
        AUTHORIZED_DATASET_SHA,
        AUTHORIZED_READINESS_SHA,
        AUTHORIZED_SURFACE_RECEIPT_SHA,
        AUTHORIZED_TRAINING_CONFIG_SHA256,
        EXPECTED_GATE2_ELIGIBLE_IDENTITY_SHA256,
        EXPECTED_GATE2_ELIGIBLE_ROWS,
        EXPECTED_TRAIN_IDENTITY_LIST_SHA256,
        EXPECTED_TRAIN_ROWS,
        EXPECTED_TRAIN_SPLIT_SHA256,
        EXPECTED_VALIDATION_IDENTITY_LIST_SHA256,
        EXPECTED_VALIDATION_ROWS,
        EXPECTED_VALIDATION_SPLIT_SHA256,
        EXPERIMENT_ID,
        INITIALIZATION_POLICY,
        LITERAL_GATE1_WEIGHTS,
        LITERAL_GATE2_WEIGHTS,
        PARENT_STAGE_A_BEST_SHA,
        SPENT_RESERVE_OVERLAP,
        generalization_runner_authorization_checks,
        split_lines_sha256,
        verify_v1r1_split_pins,
    )

    if not AUTH_FILE.exists() or not RESOLVED.exists() or not WEIGHTS.exists():
        fail("authorization artifacts missing; run authorize first")
    auth = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    resolved = json.loads(RESOLVED.read_text(encoding="utf-8"))
    weights = json.loads(WEIGHTS.read_text(encoding="utf-8"))
    init_policy = json.loads(
        (AUTH_DEST / "INITIALIZATION_POLICY.json").read_text(encoding="utf-8")
    )
    dataset_sha = sha256_file(DATASET)
    readiness_sha = sha256_file(SURFACE / "READINESS.json")
    readiness = json.loads((SURFACE / "READINESS.json").read_text(encoding="utf-8"))
    surface_state = "PASS" if readiness.get("state") == "READY" else "FAIL"
    current_best = sudo_sha256(BEST_WEIGHTS)

    if auth.get("receipt_sha256") != AUTHORIZED_AUTH_RECEIPT_SHA256:
        fail(f"auth_receipt_mismatch:{auth.get('receipt_sha256')}")
    if auth.get("receipt_sha256") != AUTHORIZED_AUTH_SHA:
        fail("auth_receipt_local_pin_mismatch")
    if dataset_sha != AUTHORIZED_DATASET_SHA or dataset_sha != DATASET_SHA:
        fail(f"dataset not authorized:{dataset_sha}")
    if readiness_sha != AUTHORIZED_READINESS_SHA or readiness_sha != READINESS_SHA:
        fail(f"readiness not authorized:{readiness_sha}")
    if auth.get("SURFACE_RECEIPT_SHA256") != AUTHORIZED_SURFACE_RECEIPT_SHA:
        fail("surface_receipt mismatch")
    if auth.get("SURFACE_RECEIPT_SHA256") != SURFACE_RECEIPT_SHA:
        fail("surface_receipt local pin mismatch")
    if resolved.get("training_config_sha256") != AUTHORIZED_TRAINING_CONFIG_SHA256:
        fail("resolved training_config_sha256 mismatch")
    if auth.get("TRAINING_CONFIG_SHA256") != AUTHORIZED_CONFIG_SHA:
        fail("auth training_config_sha256 mismatch")
    if weights.get("CLASS_WEIGHT_ARTIFACT_SHA256") != AUTHORIZED_WEIGHT_SHA:
        fail("class_weight_artifact_sha mismatch")
    if auth.get("CLASS_WEIGHT_ARTIFACT_SHA256") != AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256:
        fail("auth class_weight_artifact_sha mismatch")
    if auth.get("ARCHITECTURE_RECEIPT_SHA256") != ARCHITECTURE_RECEIPT_SHA256:
        fail("architecture_receipt mismatch")
    if auth.get("EXPERIMENT_ID") != EXPERIMENT_ID:
        fail(f"unexpected experiment:{auth.get('EXPERIMENT_ID')}")
    if auth.get("AUTHORIZE_RULE") != AUTHORIZE_RULE:
        fail(f"unexpected authorize_rule:{auth.get('AUTHORIZE_RULE')}")
    if auth.get("TRAINING_RUN_LIMIT") != 1:
        fail("training_run_limit_mismatch")
    if resolved.get("gate1_class_weights_literal") != LITERAL_GATE1_WEIGHTS:
        fail("gate1 literal weights mismatch")
    if resolved.get("gate2_class_weights_literal") != LITERAL_GATE2_WEIGHTS:
        fail("gate2 literal weights mismatch")
    if weights.get("literal_weights", {}).get("gate1") != LITERAL_G1:
        fail("weight artifact gate1 literal mismatch")
    if weights.get("literal_weights", {}).get("gate2") != LITERAL_G2:
        fail("weight artifact gate2 literal mismatch")
    if current_best != AUTHORIZED_BEST_SHA or current_best != BEST_SHA:
        fail("MODEL_WIDE_BEST weights changed")
    if auth.get("PARENT_STAGE_A_BEST") != PARENT_STAGE_A_BEST_SHA:
        fail("PARENT_STAGE_A_BEST mismatch")
    if auth.get("PARENT_STAGE_A_BEST") != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST local pin mismatch")
    if auth.get("spent_reserve_overlap", SPENT_RESERVE_OVERLAP) != 0:
        fail("spent_reserve_overlap_nonzero")
    if init_policy.get("stage_a_best_continuation") is not False:
        fail("initialization_policy_continuation_forbidden")
    if init_policy.get("base_encoder_sha256") != BEST_SHA:
        fail("initialization_policy_base_encoder_mismatch")
    if INITIALIZATION_POLICY["stage_a_best_continuation"] is not False:
        fail("module_initialization_policy_conflict")

    rows = load_jsonl(DATASET)
    gold = admission_invariants(rows)
    label_mapping = "PASS" if gold.get("pass") else "FAIL"
    stats = json.loads(
        (AUTH_DEST / "LABEL_PROVENANCE_STATS.json").read_text(encoding="utf-8")
    )
    invalid_prov = int(stats.get("invalid_provenance_rows", 1))

    train_rows = [row for row in rows if row.get("split") == "train"]
    val_rows = [row for row in rows if row.get("split") == "validation"]
    train_split_sha = split_lines_sha256(str(DATASET), split="train")
    val_split_sha = split_lines_sha256(str(DATASET), split="validation")
    train_id_sha = identity_list_sha256([r["identity"] for r in train_rows])
    val_id_sha = identity_list_sha256([r["identity"] for r in val_rows])
    gate2_eligible_ids = sorted(
        str(r["identity"])
        for r in train_rows
        if str(r["evidence_label"]) in {"EVIDENCE_PRESENT", "UNCERTAIN"}
    )
    gate2_elig_sha = identity_list_sha256(gate2_eligible_ids)
    split_pin = verify_v1r1_split_pins(
        train_rows=train_rows,
        validation_rows=val_rows,
        train_split_sha256=train_split_sha,
        validation_split_sha256=val_split_sha,
        train_identity_list_sha256=train_id_sha,
        validation_identity_list_sha256=val_id_sha,
    )
    if not split_pin["pass"]:
        fail(f"split_pin_failed:{split_pin}")
    if len(train_rows) != EXPECTED_TRAIN_ROWS or len(val_rows) != EXPECTED_VALIDATION_ROWS:
        fail("train_val_count_mismatch")
    if len(gate2_eligible_ids) != EXPECTED_GATE2_ELIGIBLE_ROWS:
        fail("gate2_eligible_count_mismatch")
    if gate2_elig_sha != EXPECTED_GATE2_ELIGIBLE_IDENTITY_SHA256:
        fail("gate2_eligible_identity_mismatch")
    if train_id_sha != EXPECTED_TRAIN_IDENTITY_LIST_SHA256:
        fail("train_identity_mismatch")
    if val_id_sha != EXPECTED_VALIDATION_IDENTITY_LIST_SHA256:
        fail("validation_identity_mismatch")
    if train_split_sha != EXPECTED_TRAIN_SPLIT_SHA256:
        fail("train_split_mismatch")
    if val_split_sha != EXPECTED_VALIDATION_SPLIT_SHA256:
        fail("validation_split_mismatch")

    checks = generalization_runner_authorization_checks(
        train_authorized=bool(auth.get("TRAIN_AUTHORIZED") or auth.get("train_authorized")),
        experiment_id=str(auth.get("EXPERIMENT_ID") or ""),
        dataset_sha256=dataset_sha,
        architecture_receipt_sha256=str(auth.get("ARCHITECTURE_RECEIPT_SHA256") or ""),
        resolved_config_sha256=str(resolved.get("training_config_sha256") or ""),
        authorized_config_sha256=str(auth.get("TRAINING_CONFIG_SHA256") or ""),
        best_sha256=current_best,
        stage_a_best_sha256=str(auth.get("PARENT_STAGE_A_BEST") or ""),
        surface_readiness=surface_state,
        label_mapping=label_mapping,
        label_provenance_invalid_rows=invalid_prov,
        prior_run_count=1 if auth.get("train_run_completed") else 0,
        reserve_consumed=bool(auth.get("RESERVE_CONSUMED", True)),
        class_weight_artifact_sha256=str(
            weights.get("CLASS_WEIGHT_ARTIFACT_SHA256") or ""
        ),
        authorized_class_weight_artifact_sha256=str(
            auth.get("CLASS_WEIGHT_ARTIFACT_SHA256") or ""
        ),
        readiness_sha256=readiness_sha,
        surface_receipt_sha256=str(auth.get("SURFACE_RECEIPT_SHA256") or ""),
        initialization_stage_a_best_continuation=bool(
            init_policy.get("stage_a_best_continuation")
        ),
    )
    if not checks["pass"]:
        fail(f"authorization_gate_failed:{json.dumps(checks, sort_keys=True)}")
    if auth.get("TRAINING_STATUS") not in {"AUTHORIZED_NOT_STARTED", "RUNNING"}:
        fail(f"training_status_blocked:{auth.get('TRAINING_STATUS')}")
    if auth.get("train_run_completed"):
        fail("training_run_count_already_nonzero")
    if (RUN_ROOT / "RUN_RECEIPT.json").exists():
        fail("prior_run_receipt_present")
    return {
        "auth": auth,
        "resolved": resolved,
        "weights": weights,
        "checks": checks,
        "dataset_sha": dataset_sha,
        "readiness": readiness,
        "readiness_sha": readiness_sha,
        "rows": rows,
        "label_mapping": label_mapping,
        "invalid_prov": invalid_prov,
        "gate2_eligible_identity_sha256": gate2_elig_sha,
        "split_pin": split_pin,
    }


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
            "UNCERTAIN_recall": metrics["by_label"]["UNCERTAIN"]["recall"],
            "false_evidence_entry_rate_on_none": metrics[
                "false_evidence_entry_rate_on_none"
            ],
            "n": len(indices),
            "stage_a_macro_f1": metrics["stage_a_macro_f1"],
        }
    return out


def inner() -> int:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file, save_file

    from hyperlexical.classification_v2_surface import surface_form
    from hyperlexical.classification_v5_stage_a import (
        TRAIN_HYPERPARAMS,
        canonical_json,
        evaluate_decisions,
        sha256_text,
    )
    from hyperlexical.classification_v5_stage_a_two_stage import (
        ARCHITECTURE_RECEIPT_SHA256,
        DROP_LAST,
        GATE1_LABELS,
        GATE2_LABELS,
        LAMBDA_GATE2,
        calibrate_two_stage_thresholds,
        checkpoint_selection_score,
        component_gate_metrics,
        decide_two_stage,
        full_pass_batch_indices,
        gate1_confusion_matrix,
        gate1_false_possible_entry_rate,
        gate1_probabilities,
        gate1_target,
        gate2_confusion_matrix,
        gate2_eligible,
        gate2_probabilities,
        gate2_target,
        route_diagnostics,
        select_checkpoint,
    )
    from hyperlexical.classification_v5_stage_a_two_stage_generalization import (
        AUTHORIZED_BEST_SHA,
        EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,
        EXPECTED_TRAIN_ROWS,
        EXPERIMENT_ID,
        INITIALIZATION_POLICY,
        LITERAL_GATE1_WEIGHTS,
        LITERAL_GATE2_WEIGHTS,
        PARENT_STAGE_A_BEST_SHA,
        SPENT_RESERVE,
        SPENT_RESERVE_OVERLAP,
        SPENT_RESERVE_STATUS,
        TRAIN_RULE,
        build_v1r1_two_stage_split_witness,
        cell_route_diagnostics,
        compare_to_stage_a_best,
        row_length_band,
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
    rows = pins["rows"]

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

    auth["TRAINING_STATUS"] = "RUNNING"
    write_private(AUTH_FILE, auth)

    disjoint = json.loads(DISJOINTNESS.read_text(encoding="utf-8"))
    witness = build_v1r1_two_stage_split_witness(
        rows,
        dataset_sha256=pins["dataset_sha"],
        dataset_path=str(DATASET),
        code_revision=str(resolved.get("code_revision") or ""),
        disjointness=disjoint,
    )
    write_private(RUN_ROOT / "TWO_STAGE_SPLIT_WITNESS.json", witness)
    write_private(AUTH_DEST / "TWO_STAGE_SPLIT_WITNESS.json", witness)

    train_rows = [row for row in rows if row.get("split") == "train"]
    val_rows = [row for row in rows if row.get("split") == "validation"]
    if len(train_rows) != EXPECTED_TRAIN_ROWS:
        fail("train_rows_mismatch_after_witness")
    if int(witness["optimizer_steps_per_epoch"]) != EXPECTED_OPTIMIZER_STEPS_PER_EPOCH:
        fail("optimizer_steps_per_epoch_mismatch")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("Stage A two-stage train requires CUDA")

    # Hard ban: never load STAGE_A_BEST into trainable Stage-A state.
    stage_a_best_path = Path(
        "/home/morpheus/.hyperlex/models/"
        "hyperlex-encoder-modernbert-base-seed-classification-v5-stage-a-two-stage-001"
    )
    if os.environ.get("HLX_V5_LOAD_STAGE_A_BEST") == "1":
        fail("STAGE_A_BEST_load_forbidden_for_generalization_retrain")
    if INITIALIZATION_POLICY["stage_a_best_continuation"] is not False:
        fail("initialization_policy_forbids_continuation")

    seed = int(TRAIN_HYPERPARAMS["seed"])
    torch.manual_seed(seed)
    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    # FRESH_RETRAIN_FROM_MODEL_WIDE_BEST only — not STAGE_A_BEST cd2829c1…
    warm = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    if sudo_sha256(BEST_WEIGHTS) != AUTHORIZED_BEST_SHA:
        fail("MODEL_WIDE_BEST digest drifted before overlay")
    loaded = apply_encoder_trainable(encoder, warm.get("encoder") or {})
    if loaded["loaded"] != 48:
        fail(f"BEST encoder overlay missed tensors: loaded={loaded['loaded']}")
    trainable_params, last_n = freeze_encoder(
        encoder, last_trainable=int(TRAIN_HYPERPARAMS["last_trainable"])
    )
    gate1_head = nn.Linear(HIDDEN, 2)
    gate2_head = nn.Linear(HIDDEN, 2)
    nn.init.xavier_uniform_(gate1_head.weight)
    nn.init.zeros_(gate1_head.bias)
    nn.init.xavier_uniform_(gate2_head.weight)
    nn.init.zeros_(gate2_head.bias)

    write_private(
        RUN_ROOT / "INITIAL_CHECKPOINT.json",
        {
            "architecture_receipt_sha256": ARCHITECTURE_RECEIPT_SHA256,
            "checkpoint_role": "INITIAL",
            "dataset_sha256": pins["dataset_sha"],
            "gate_heads": ["gate1_head", "gate2_head"],
            "head_init": TRAIN_HYPERPARAMS["head_init"],
            "initialization_policy": INITIALIZATION_POLICY,
            "parent_BEST_sha256": AUTHORIZED_BEST_SHA,
            "parent_STAGE_A_BEST_sha256_reference_only": PARENT_STAGE_A_BEST_SHA,
            "reconstructible_from": {
                "best_weights_path": str(BEST_WEIGHTS),
                "head_init": TRAIN_HYPERPARAMS["head_init"],
                "seed": seed,
                "stage_a_best_path_not_loaded": str(stage_a_best_path),
                "trunk": str(TRUNK),
            },
            "schema": "hyperlex.classification.v5.stage_a_two_stage_checkpoint_manifest.v1",
            "seed": seed,
            "split_witness_sha256": witness["TWO_STAGE_SPLIT_WITNESS_SHA256"],
            "stage_a_best_continuation": False,
            "training_config_sha256": resolved["training_config_sha256"],
            "weights_duplicated": False,
        },
    )

    encoder.to(device)
    gate1_head.to(device)
    gate2_head.to(device)
    params = [
        p
        for p in list(encoder.parameters())
        + list(gate1_head.parameters())
        + list(gate2_head.parameters())
        if p.requires_grad
    ]
    optimizer = torch.optim.AdamW(
        params,
        lr=float(TRAIN_HYPERPARAMS["learning_rate"]),
        weight_decay=float(TRAIN_HYPERPARAMS["weight_decay"]),
    )

    g1_w = torch.tensor(
        [float(LITERAL_GATE1_WEIGHTS[label]) for label in GATE1_LABELS],
        dtype=torch.float32,
        device=device,
    )
    g2_w = torch.tensor(
        [float(LITERAL_GATE2_WEIGHTS[label]) for label in GATE2_LABELS],
        dtype=torch.float32,
        device=device,
    )
    loss_g1 = nn.CrossEntropyLoss(weight=g1_w, reduction="none")
    loss_g2 = nn.CrossEntropyLoss(weight=g2_w, reduction="none")
    prov_mult = {
        "OBSERVED": 1.0,
        "INFERRED": 0.5,
    }

    max_epochs = int(TRAIN_HYPERPARAMS["max_epochs"])
    min_epochs = int(TRAIN_HYPERPARAMS["minimum_epochs"])
    patience = int(TRAIN_HYPERPARAMS["early_stopping_patience"])
    batch_size = int(TRAIN_HYPERPARAMS["micro_batch_size"])
    max_len = int(TRAIN_HYPERPARAMS["max_len"] or MAX_LEN)
    warmup_ratio = float(TRAIN_HYPERPARAMS["warmup_ratio"])
    steps_per_epoch = int(witness["optimizer_steps_per_epoch"])
    if steps_per_epoch != math.ceil(EXPECTED_TRAIN_ROWS / batch_size):
        fail("dataloader_len_inconsistent_with_drop_last_false")
    total_planned_steps = max_epochs * steps_per_epoch
    warmup_steps = max(1, int(warmup_ratio * total_planned_steps))
    base_lr = float(TRAIN_HYPERPARAMS["learning_rate"])

    def set_lr(step: int) -> None:
        if step < warmup_steps:
            scale = float(step + 1) / float(warmup_steps)
        else:
            scale = 1.0
        for group in optimizer.param_groups:
            group["lr"] = base_lr * scale

    candidates = []
    best_record = None
    best_state = None
    best_epoch = 0
    stale = 0
    epoch_trace = []
    optimizer_steps = 0
    started = time.time()
    metrics_path = RUN_ROOT / "METRICS.jsonl"
    if metrics_path.exists():
        metrics_path.unlink()

    def score_split(split_rows: list[dict]):
        encoder.eval()
        gate1_head.eval()
        gate2_head.eval()
        golds, p_possible, p_confirmed = [], [], []
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
                g1 = gate1_probabilities(gate1_head(pooled)[0].detach().cpu().tolist())
                g2 = gate2_probabilities(gate2_head(pooled)[0].detach().cpu().tolist())
                golds.append(str(row["evidence_label"]))
                p_possible.append(float(g1["POSSIBLE_EVIDENCE"]))
                p_confirmed.append(float(g2["CONFIRMED_PRESENT"]))
        return golds, p_possible, p_confirmed

    def capture_weights():
        return {
            "encoder": {
                k: v.detach().cpu().clone()
                for k, v in collect_encoder_trainable(encoder).items()
            },
            "gate1_bias": gate1_head.bias.detach().cpu().clone(),
            "gate1_weight": gate1_head.weight.detach().cpu().clone(),
            "gate2_bias": gate2_head.bias.detach().cpu().clone(),
            "gate2_weight": gate2_head.weight.detach().cpu().clone(),
        }

    def save_tmp_checkpoint(epoch: int, role: str, state: dict) -> Path:
        path = tmp_ckpt_root / f"checkpoint-{epoch:04d}-{role}"
        path.mkdir(parents=True, exist_ok=True)
        flat = flatten_weight_tensors(
            {
                "encoder": state["encoder"],
                "gate1_head": {
                    "weight": state["gate1_weight"].contiguous(),
                    "bias": state["gate1_bias"].contiguous(),
                },
                "gate2_head": {
                    "weight": state["gate2_weight"].contiguous(),
                    "bias": state["gate2_bias"].contiguous(),
                },
            }
        )
        save_file(flat, str(path / "model.safetensors"))
        write_private(path / "meta.json", {"epoch": epoch, "role": role, "temporary": True})
        return path

    # Verify split witness before first optimizer step.
    if witness["train_rows"] != EXPECTED_TRAIN_ROWS:
        fail("split_witness_train_rows")
    if witness["drop_last"] is not False:
        fail("split_witness_drop_last")

    for epoch in range(max_epochs):
        encoder.train()
        gate1_head.train()
        gate2_head.train()
        batches = full_pass_batch_indices(
            len(train_rows),
            batch_size=batch_size,
            seed=seed + epoch,
            drop_last=DROP_LAST,
        )
        if len(batches) != steps_per_epoch:
            fail(f"epoch_batch_count_mismatch:{len(batches)}!={steps_per_epoch}")
        seen = sum(len(b) for b in batches)
        if seen != EXPECTED_TRAIN_ROWS:
            fail(f"epoch_row_cover_mismatch:{seen}")

        running = 0.0
        n_batches = 0
        for batch_indices in batches:
            texts = [str(train_rows[i]["text"]) for i in batch_indices]
            g1_targets = torch.tensor(
                [gate1_target(str(train_rows[i]["evidence_label"])) for i in batch_indices],
                dtype=torch.long,
                device=device,
            )
            g2_mask = torch.tensor(
                [
                    1.0 if gate2_eligible(str(train_rows[i]["evidence_label"])) else 0.0
                    for i in batch_indices
                ],
                dtype=torch.float32,
                device=device,
            )
            g2_targets = torch.tensor(
                [
                    gate2_target(str(train_rows[i]["evidence_label"]))
                    if gate2_eligible(str(train_rows[i]["evidence_label"]))
                    else 0
                    for i in batch_indices
                ],
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
            logits1 = gate1_head(pooled)
            logits2 = gate2_head(pooled)
            per_g1 = loss_g1(logits1, g1_targets) * sample_w
            l_gate1 = per_g1.mean()
            if float(g2_mask.sum().item()) > 0:
                per_g2 = loss_g2(logits2, g2_targets) * sample_w * g2_mask
                l_gate2 = per_g2.sum() / g2_mask.sum()
            else:
                l_gate2 = torch.zeros((), device=device)
            loss = l_gate1 + float(LAMBDA_GATE2) * l_gate2
            set_lr(optimizer_steps)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                params, float(TRAIN_HYPERPARAMS["max_grad_norm"])
            )
            optimizer.step()
            optimizer_steps += 1
            running += float(loss.detach().cpu())
            n_batches += 1

        val_golds, val_pp, val_pc = score_split(val_rows)
        # Checkpoint selection uses Gate metrics at mid-grid thresholds for score only;
        # final threshold search is independent and runs after restore.
        # Use 0.50/0.50 as the frozen diagnostic operating point for selection components.
        sel_g1_thresh = 0.50
        sel_g2_thresh = 0.50
        g1_preds_possible = [pp >= sel_g1_thresh for pp in val_pp]
        g1_gold = [gate1_target(g) for g in val_golds]
        g1_pred = [1 if flag else 0 for flag in g1_preds_possible]
        from hyperlexical.classification_v5_stage_a_two_stage import binary_macro_f1

        g1_macro = float(binary_macro_f1(g1_gold, g1_pred))
        g2_idx = [i for i, g in enumerate(val_golds) if gate2_eligible(g)]
        g2_gold = [gate2_target(val_golds[i]) for i in g2_idx]
        g2_pred = [
            1 if float(val_pc[i]) >= sel_g2_thresh else 0 for i in g2_idx
        ]
        g2_macro = float(binary_macro_f1(g2_gold, g2_pred))
        sel_score = checkpoint_selection_score(
            gate1_macro_f1=g1_macro, gate2_macro_f1=g2_macro
        )
        g1_false = float(
            gate1_false_possible_entry_rate(val_golds, g1_preds_possible)
        )
        # Gate2 PRESENT recall on eligible golds at selection thresholds.
        present_eligible = [
            i for i in g2_idx if val_golds[i] == "EVIDENCE_PRESENT"
        ]
        if present_eligible:
            g2_present_recall = sum(
                1 for i in present_eligible if float(val_pc[i]) >= sel_g2_thresh
            ) / len(present_eligible)
        else:
            g2_present_recall = 0.0

        cand = {
            "epoch": epoch + 1,
            "gate1_false_possible_entry_rate": g1_false,
            "gate1_macro_f1": g1_macro,
            "gate2_confirmed_present_recall": float(g2_present_recall),
            "gate2_macro_f1": g2_macro,
            "mean_train_loss": running / max(1, n_batches),
            "n_batches": n_batches,
            "optimizer_steps_cumulative": optimizer_steps,
            "selection_score": sel_score,
        }
        candidates.append(cand)
        epoch_trace.append(cand)
        with metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(cand) + "\n")
        print(json.dumps(cand, sort_keys=True), flush=True)

        chosen = select_checkpoint(candidates)
        if chosen["epoch"] == epoch + 1:
            best_record = dict(cand)
            best_epoch = epoch + 1
            best_state = capture_weights()
            save_tmp_checkpoint(best_epoch, "selected-candidate", best_state)
            stale = 0
        else:
            stale += 1
        if epoch + 1 >= min_epochs and stale >= patience:
            break

    if best_state is None or best_record is None:
        fail("no_best_checkpoint_selected")

    final_epoch = epoch_trace[-1]["epoch"] if epoch_trace else 0
    final_state = capture_weights()
    final_differs = final_epoch != best_epoch
    final_manifest = {
        "checkpoint_role": "FINAL_RUN_STATE",
        "differs_from_selected": final_differs,
        "final_epoch": final_epoch,
        "retained": final_differs,
        "schema": "hyperlex.classification.v5.stage_a_two_stage_checkpoint_manifest.v1",
        "selected_epoch": best_epoch,
    }
    if final_differs:
        final_dir = RUN_ROOT / "final_run_state"
        final_dir.mkdir(mode=0o700, exist_ok=True)
        flat_final = flatten_weight_tensors(
            {
                "encoder": final_state["encoder"],
                "gate1_head": {
                    "weight": final_state["gate1_weight"].contiguous(),
                    "bias": final_state["gate1_bias"].contiguous(),
                },
                "gate2_head": {
                    "weight": final_state["gate2_weight"].contiguous(),
                    "bias": final_state["gate2_bias"].contiguous(),
                },
            }
        )
        save_file(flat_final, str(final_dir / "model.safetensors"))
        final_manifest["checkpoint_sha256"] = sha256_file(
            final_dir / "model.safetensors"
        )
        final_manifest["path"] = str(final_dir / "model.safetensors")
    write_private(RUN_ROOT / "FINAL_RUN_STATE.json", final_manifest)

    apply_encoder_trainable(encoder, best_state["encoder"])
    with torch.no_grad():
        gate1_head.weight.copy_(best_state["gate1_weight"].to(device))
        gate1_head.bias.copy_(best_state["gate1_bias"].to(device))
        gate2_head.weight.copy_(best_state["gate2_weight"].to(device))
        gate2_head.bias.copy_(best_state["gate2_bias"].to(device))

    val_golds, val_pp, val_pc = score_split(val_rows)
    calibration = calibrate_two_stage_thresholds(
        golds=val_golds, p_possible=val_pp, p_confirmed=val_pc
    )
    if not calibration["feasible"]:
        disposition = "SETTLED_FAIL"
        chosen_thr = {"gate1_threshold": None, "gate2_present_threshold": None}
        # Fail-display pair for diagnostics only.
        g1_thr, g2_thr = 0.50, 0.50
        promotion_candidate = False
    else:
        disposition = "SETTLED_PASS"
        chosen_thr = {
            "gate1_threshold": calibration["chosen"]["gate1_threshold"],
            "gate2_present_threshold": calibration["chosen"]["gate2_present_threshold"],
        }
        g1_thr = float(chosen_thr["gate1_threshold"])
        g2_thr = float(chosen_thr["gate2_present_threshold"])
        promotion_candidate = True

    val_decisions = [
        decide_two_stage(
            p_possible=float(pp),
            p_confirmed=float(pc),
            gate1_threshold=g1_thr,
            gate2_present_threshold=g2_thr,
        )
        for pp, pc in zip(val_pp, val_pc)
    ]
    val_metrics = evaluate_decisions(val_golds, val_decisions)
    if not val_metrics["acceptance_pass"]:
        disposition = "SETTLED_FAIL"
        promotion_candidate = False

    component = component_gate_metrics(
        golds=val_golds,
        p_possible=val_pp,
        p_confirmed=val_pc,
        gate1_threshold=g1_thr,
        gate2_present_threshold=g2_thr,
    )
    routes = route_diagnostics(
        golds=val_golds,
        p_possible=val_pp,
        p_confirmed=val_pc,
        gate1_threshold=g1_thr,
        gate2_present_threshold=g2_thr,
        rows=val_rows,
    )
    g1_conf = gate1_confusion_matrix(
        val_golds, p_possible=val_pp, gate1_threshold=g1_thr
    )
    g2_conf = gate2_confusion_matrix(
        val_golds,
        p_possible=val_pp,
        p_confirmed=val_pc,
        gate1_threshold=g1_thr,
        gate2_present_threshold=g2_thr,
    )

    selected_dir = RUN_ROOT / "selected"
    flat = flatten_weight_tensors(
        {
            "encoder": collect_encoder_trainable(encoder),
            "gate1_head": {
                "weight": gate1_head.weight.detach().cpu().contiguous(),
                "bias": gate1_head.bias.detach().cpu().contiguous(),
            },
            "gate2_head": {
                "weight": gate2_head.weight.detach().cpu().contiguous(),
                "bias": gate2_head.bias.detach().cpu().contiguous(),
            },
        }
    )
    selected_weights = selected_dir / "model.safetensors"
    save_file(flat, str(selected_weights))
    selected_config = {
        "BEST_MUTATED": False,
        "architecture_receipt_sha256": ARCHITECTURE_RECEIPT_SHA256,
        "class_weight_artifact_sha256": AUTHORIZED_WEIGHT_SHA,
        "code_revision": resolved.get("code_revision"),
        "dataset_sha256": pins["dataset_sha"],
        "experiment_id": EXPERIMENT_ID,
        "gate1_thresholds_selected": chosen_thr.get("gate1_threshold"),
        "gate2_present_threshold_selected": chosen_thr.get("gate2_present_threshold"),
        "hidden_size": HIDDEN,
        "init_from": str(INIT_FROM),
        "last_trainable": last_n,
        "parent_BEST_sha256": AUTHORIZED_BEST_SHA,
        "pooling": TRAIN_HYPERPARAMS["pooling"],
        "promotion_candidate": promotion_candidate,
        "resolved_training_config_sha256": resolved["training_config_sha256"],
        "restored_epoch": best_epoch,
        "rule": TRAIN_RULE,
        "schema": "hyperlex.classification.v5.stage_a_two_stage_selected_config.v1",
        "seed": seed,
        "selection_score": best_record["selection_score"],
        "split_witness_sha256": witness["TWO_STAGE_SPLIT_WITNESS_SHA256"],
        "tokenizer_identity": resolved["tokenization"]["tokenizer_identity"],
        "trainable_encoder_params": trainable_params,
        "training_config_sha256": resolved["training_config_sha256"],
    }
    write_private(selected_dir / "config.json", selected_config)
    checkpoint_sha = sha256_file(selected_weights)
    write_private(
        RUN_ROOT / "SELECTED_CHECKPOINT.json",
        {
            **selected_config,
            "checkpoint_role": "SELECTED",
            "checkpoint_sha256": checkpoint_sha,
            "path": str(selected_weights),
            "weights_loadable_without_trainer_state": True,
        },
    )

    OUT.mkdir(parents=True, exist_ok=True)
    os.chmod(OUT, 0o755)
    shutil.copy2(selected_weights, OUT / "model.safetensors")
    write_private(OUT / "stage_a_two_stage_config.json", selected_config)

    by_prov = slice_diagnostics(
        val_rows, val_golds, val_decisions, key_fn=lambda r: r.get("provenance") or "UNKNOWN"
    )
    by_atom = slice_diagnostics(
        val_rows, val_golds, val_decisions, key_fn=lambda r: surface_form(str(r["text"]))
    )
    by_source = slice_diagnostics(
        val_rows, val_golds, val_decisions, key_fn=source_bucket
    )
    by_source_family = slice_diagnostics(
        val_rows,
        val_golds,
        val_decisions,
        key_fn=lambda r: r.get("source_family") or "unknown",
    )
    by_domain = slice_diagnostics(
        val_rows,
        val_golds,
        val_decisions,
        key_fn=lambda r: r.get("topic_domain") or "unspecified",
    )
    by_length = slice_diagnostics(
        val_rows, val_golds, val_decisions, key_fn=row_length_band
    )
    by_reason = slice_diagnostics(
        val_rows,
        val_golds,
        val_decisions,
        key_fn=lambda r: r.get("ambiguity_reason") or "NONE",
    )
    by_primary_cell = cell_route_diagnostics(
        rows=val_rows,
        golds=val_golds,
        p_possible=val_pp,
        p_confirmed=val_pc,
        gate1_threshold=g1_thr,
        gate2_present_threshold=g2_thr,
    )
    stage_a_best_comparison = compare_to_stage_a_best(
        {
            "EVIDENCE_PRESENT_recall": val_metrics["by_label"]["EVIDENCE_PRESENT"][
                "recall"
            ],
            "NO_EVIDENCE_recall": val_metrics["by_label"]["NO_EVIDENCE"]["recall"],
            "UNCERTAIN_recall": val_metrics["by_label"]["UNCERTAIN"]["recall"],
            "false_evidence_entry_rate_on_none": val_metrics[
                "false_evidence_entry_rate_on_none"
            ],
            "stage_a_macro_f1": val_metrics["stage_a_macro_f1"],
        }
    )

    acceptance_table = {
        "EVIDENCE_PRESENT_recall": {
            "gate": 0.70,
            "pass": val_metrics["by_label"]["EVIDENCE_PRESENT"]["recall"] >= 0.70,
            "value": val_metrics["by_label"]["EVIDENCE_PRESENT"]["recall"],
        },
        "NO_EVIDENCE_recall": {
            "gate": 0.90,
            "pass": val_metrics["by_label"]["NO_EVIDENCE"]["recall"] >= 0.90,
            "value": val_metrics["by_label"]["NO_EVIDENCE"]["recall"],
        },
        "false_evidence_entry_rate_on_none": {
            "gate": 0.05,
            "pass": val_metrics["false_evidence_entry_rate_on_none"] <= 0.05,
            "value": val_metrics["false_evidence_entry_rate_on_none"],
        },
    }

    write_private(
        RUN_ROOT / "diagnostics" / "threshold_grid.json",
        {
            "disposition": calibration["disposition"],
            "feasible": calibration["feasible"],
            "n_candidates": calibration["n_candidates"],
            "n_passing": calibration["n_passing"],
            "chosen": calibration.get("chosen"),
            "grid_results": calibration.get("grid_results"),
        },
    )
    write_private(
        RUN_ROOT / "diagnostics" / "route_diagnostics.json",
        routes,
    )
    write_private(
        RUN_ROOT / "diagnostics" / "component_metrics.json",
        component,
    )
    write_private(
        RUN_ROOT / "diagnostics" / "confusion.json",
        {
            "end_to_end": routes.get("end_to_end_confusion"),
            "gate1": g1_conf,
            "gate2": g2_conf,
        },
    )
    write_private(
        RUN_ROOT / "diagnostics" / "strata.json",
        {
            "by_ATOM_PROSE": by_atom,
            "by_ambiguity_reason": by_reason,
            "by_domain": by_domain,
            "by_length_band": by_length,
            "by_primary_cell": by_primary_cell,
            "by_provenance": by_prov,
            "by_source": by_source,
            "by_source_family": by_source_family,
        },
    )
    write_private(
        RUN_ROOT / "diagnostics" / "generalization_cells.json",
        by_primary_cell,
    )
    write_private(
        RUN_ROOT / "diagnostics" / "stage_a_best_comparison.json",
        stage_a_best_comparison,
    )

    elapsed = time.time() - started
    receipt = {
        "ARCHITECTURE_RECEIPT_SHA256": ARCHITECTURE_RECEIPT_SHA256,
        "AUTHORIZATION_RECEIPT_SHA256": AUTHORIZED_AUTH_SHA,
        "BEST": "UNCHANGED",
        "BEST_MUTATED": False,
        "CLASS_WEIGHT_ARTIFACT_SHA256": AUTHORIZED_WEIGHT_SHA,
        "CURRENT_BEST": AUTHORIZED_BEST_SHA,
        "DATASET_SHA256": pins["dataset_sha"],
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "MODEL_WIDE_BEST": AUTHORIZED_BEST_SHA,
        "MODEL_WIDE_BEST_MUTATED": False,
        "PARENT_STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
        "RESERVE": SPENT_RESERVE_STATUS,
        "RESERVE_CONSUMED": False,
        "RUN_RECEIPT_SHA256": None,
        "SCIENTIFIC_RESULT": disposition,
        "SELECTED_CHECKPOINT_SHA256": checkpoint_sha,
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_OVERLAP": SPENT_RESERVE_OVERLAP,
        "STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
        "STAGE_A_BEST_MUTATED": False,
        "TRAIN": True,
        "TRAINING_CONFIG_SHA256": resolved["training_config_sha256"],
        "TRAINING_STATUS": "COMPLETE",
        "TWO_STAGE_SPLIT_WITNESS_SHA256": witness["TWO_STAGE_SPLIT_WITNESS_SHA256"],
        "acceptance_gates": acceptance_table,
        "actual_optimizer_steps": optimizer_steps,
        "component_metrics": component,
        "elapsed_seconds": elapsed,
        "end_to_end_confusion": routes.get("end_to_end_confusion"),
        "epochs_ran": final_epoch,
        "gate1_confusion": g1_conf,
        "gate2_confusion": g2_conf,
        "generalization_cells": by_primary_cell,
        "initialization_policy": INITIALIZATION_POLICY["policy"],
        "optimizer_steps_per_epoch": steps_per_epoch,
        "promotion_candidate": promotion_candidate,
        "restored_epoch": best_epoch,
        "route_diagnostics": {
            "NONE_FP": routes["NONE_FP"],
            "PRESENT_FN": routes["PRESENT_FN"],
            "UNCERTAIN": routes["UNCERTAIN"],
        },
        "rule": TRAIN_RULE,
        "schema": (
            "hyperlex.classification.v5."
            "stage_a_two_stage_generalization_train_receipt.v1"
        ),
        "selected_thresholds": chosen_thr,
        "selection_score": best_record["selection_score"],
        "stage_a_best_comparison": stage_a_best_comparison,
        "strata": {
            "by_ATOM_PROSE": by_atom,
            "by_length_band": by_length,
            "by_primary_cell": by_primary_cell,
            "by_provenance": by_prov,
            "by_source_family": by_source_family,
        },
        "threshold_grid": {
            "disposition": calibration["disposition"],
            "n_candidates": calibration["n_candidates"],
            "n_passing": calibration["n_passing"],
        },
        "train_dataloader_len": steps_per_epoch,
        "train_rows": EXPECTED_TRAIN_ROWS,
        "validation_metrics": {
            "EVIDENCE_PRESENT_recall": val_metrics["by_label"]["EVIDENCE_PRESENT"][
                "recall"
            ],
            "NO_EVIDENCE_recall": val_metrics["by_label"]["NO_EVIDENCE"]["recall"],
            "UNCERTAIN_recall": val_metrics["by_label"]["UNCERTAIN"]["recall"],
            "false_evidence_entry_rate_on_none": val_metrics[
                "false_evidence_entry_rate_on_none"
            ],
            "stage_a_macro_f1": val_metrics["stage_a_macro_f1"],
        },
        "weights_dir": str(selected_dir),
    }
    receipt["RUN_RECEIPT_SHA256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "RUN_RECEIPT_SHA256"})
    )
    # Alias for schema required field name.
    receipt["receipt_sha256"] = receipt["RUN_RECEIPT_SHA256"]
    write_private(RUN_ROOT / "RUN_RECEIPT.json", receipt)
    write_private(AUTH_DEST / "STAGE_A_TWO_STAGE_GENERALIZATION_TRAIN.json", receipt)

    for name in (
        "AUTHORIZATION.json",
        "RESOLVED_TRAINING_CONFIG.json",
        "V1R1_TWO_STAGE_CLASS_WEIGHTS.json",
        "TWO_STAGE_SPLIT_WITNESS.json",
        "INITIALIZATION_POLICY.json",
    ):
        src = AUTH_DEST / name
        dst_name = (
            "TRAINING_CONFIG.json"
            if name == "RESOLVED_TRAINING_CONFIG.json"
            else name
        )
        dst = RUN_ROOT / dst_name
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)

    if tmp_ckpt_root.exists():
        shutil.rmtree(tmp_ckpt_root)
    del optimizer

    auth["TRAINING_STATUS"] = "COMPLETE"
    auth["train_run_completed"] = True
    auth["scientific_disposition"] = disposition
    auth["promotion_candidate"] = promotion_candidate
    auth["selected_checkpoint_sha256"] = checkpoint_sha
    auth["run_receipt_sha256"] = receipt["RUN_RECEIPT_SHA256"]
    write_private(AUTH_FILE, auth)

    summary = {
        "BEST_MUTATED": False,
        "MODEL_WIDE_BEST_MUTATED": False,
        "RESERVE": SPENT_RESERVE_STATUS,
        "SCIENTIFIC_RESULT": disposition,
        "SELECTED_CHECKPOINT_SHA256": checkpoint_sha,
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_OVERLAP": SPENT_RESERVE_OVERLAP,
        "STAGE_A_BEST_MUTATED": False,
        "TRAINING_STATUS": "COMPLETE",
        "disposition": disposition,
        "epochs_ran": final_epoch,
        "false_evidence_entry_rate_on_none": val_metrics[
            "false_evidence_entry_rate_on_none"
        ],
        "gate1_threshold": chosen_thr.get("gate1_threshold"),
        "gate2_present_threshold": chosen_thr.get("gate2_present_threshold"),
        "generalization_cells": {
            cell: by_primary_cell.get(cell)
            for cell in (
                "SHORT_ATOM/NO_EVIDENCE",
                "SHORT_ATOM/EVIDENCE_PRESENT",
                "DEFINITION_STYLE/NO_EVIDENCE",
                "DEFINITION_STYLE/EVIDENCE_PRESENT",
                "PROSE/NO_EVIDENCE",
                "PROSE/EVIDENCE_PRESENT",
                "ORDINARY_PROSE/NO_EVIDENCE",
                "ORDINARY_PROSE/EVIDENCE_PRESENT",
            )
        },
        "n_threshold_passing": calibration["n_passing"],
        "optimizer_steps": optimizer_steps,
        "promotion_candidate": promotion_candidate,
        "receipt_sha256": receipt["RUN_RECEIPT_SHA256"],
        "restored_epoch": best_epoch,
        "selection_score": best_record["selection_score"],
        "split_witness_sha256": witness["TWO_STAGE_SPLIT_WITNESS_SHA256"],
        "stage_a_best_comparison": stage_a_best_comparison,
        "stage_a_macro_f1": val_metrics["stage_a_macro_f1"],
        "EVIDENCE_PRESENT_recall": val_metrics["by_label"]["EVIDENCE_PRESENT"]["recall"],
        "NO_EVIDENCE_recall": val_metrics["by_label"]["NO_EVIDENCE"]["recall"],
        "UNCERTAIN_recall": val_metrics["by_label"]["UNCERTAIN"]["recall"],
        "component_metrics": component,
        "route_diagnostics": receipt["route_diagnostics"],
        "run_root": str(RUN_ROOT),
        "by_provenance": by_prov,
        "by_source_family": by_source_family,
        "by_domain": by_domain,
        "by_length_band": by_length,
    }
    write_private(RUN_ROOT / "SUMMARY.json", summary)
    write_private(AUTH_DEST / "TRAIN_SUMMARY.json", summary)

    # Public mirrors (no private row bodies).
    write_repo(REPO_ARTIFACTS / "train_once_summary.json", summary)
    write_repo(
        REPO_ARTIFACTS / "train_once_receipt.json",
        {
            "AUTHORIZATION_RECEIPT_SHA256": AUTHORIZED_AUTH_SHA,
            "BEST": "UNCHANGED",
            "CLASS_WEIGHT_ARTIFACT_SHA256": AUTHORIZED_WEIGHT_SHA,
            "DATASET_SHA256": pins["dataset_sha"],
            "EXPERIMENT_ID": EXPERIMENT_ID,
            "MODEL_WIDE_BEST_MUTATED": False,
            "RESERVE": SPENT_RESERVE_STATUS,
            "RUN_RECEIPT_SHA256": receipt["RUN_RECEIPT_SHA256"],
            "SCIENTIFIC_RESULT": disposition,
            "SELECTED_CHECKPOINT_SHA256": checkpoint_sha,
            "SPENT_RESERVE": SPENT_RESERVE,
            "STAGE_A_BEST_MUTATED": False,
            "TRAINING_CONFIG_SHA256": resolved["training_config_sha256"],
            "TRAINING_STATUS": "COMPLETE",
            "TWO_STAGE_SPLIT_WITNESS_SHA256": witness["TWO_STAGE_SPLIT_WITNESS_SHA256"],
            "acceptance_gates": acceptance_table,
            "component_metrics": component,
            "generalization_cells": summary["generalization_cells"],
            "n_threshold_passing": calibration["n_passing"],
            "promotion_candidate": promotion_candidate,
            "restored_epoch": best_epoch,
            "route_diagnostics": receipt["route_diagnostics"],
            "selected_thresholds": chosen_thr,
            "selection_score": best_record["selection_score"],
            "stage_a_best_comparison": stage_a_best_comparison,
            "validation_metrics": receipt["validation_metrics"],
            "train": True,
        },
    )
    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-two-stage-generalization-train-once-receipt-20261001.json",
        json.loads((REPO_ARTIFACTS / "train_once_receipt.json").read_text()),
    )

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V5_STAGE_A_EXECUTE_GENERALIZATION_TRAIN") != "1":
        try:
            pins = require_authorization()
        except SystemExit:
            raise
        print(
            json.dumps(
                {
                    "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
                    "authorization_pass": True,
                    "execute_train": False,
                    "experiment_id": pins["auth"].get("EXPERIMENT_ID"),
                    "message": (
                        "authorization gates passed; set "
                        "HLX_V5_STAGE_A_EXECUTE_GENERALIZATION_TRAIN=1 to run the single train"
                    ),
                    "training_config_sha256": pins["resolved"]["training_config_sha256"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if os.environ.get("HLX_V5_STAGE_A_GENERALIZATION_TRAIN_INNER") == "1":
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
        "HLX_V5_STAGE_A_EXECUTE_GENERALIZATION_TRAIN=1",
        "-e",
        "HLX_V5_STAGE_A_GENERALIZATION_TRAIN_INNER=1",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v5_stage_a_two_stage_generalization_train.py"),
    ]
    print(json.dumps({"launch": cmd[-1], "image": IMAGE}, sort_keys=True), flush=True)
    log_path = AUTH_DEST / "train_console.log"
    AUTH_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
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
