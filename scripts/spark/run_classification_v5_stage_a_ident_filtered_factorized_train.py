"""TRAIN_STAGE_A_IDENT_FILTERED_FACTORIZED_ONCE — V1R2 factorized train.

Requires sealed AUTHORIZE_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN.
Consumes sealed IDENT_FILTERED class weights; does not recompute.
Fresh init from MODEL_WIDE_BEST (not STAGE_A_BEST / prior failed ckpts).
Does not move BEST/STAGE_A_BEST. Does not touch spent reserve.
Does not mutate V1R2, restore excluded rows, relabel, or alter Stage B.

Set HLX_V5_STAGE_A_EXECUTE_IDENT_FILTERED_FACTORIZED_TRAIN=1 to execute.
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
    "classification-v5-stage-a-identifiability-filtered-v1r2-20261001"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
EXCLUSION = SURFACE / "EXCLUSION_MANIFEST.jsonl"
DATASET_SHA = "492ed36751c7fdc40fe10bcdfabb69fa8783f8680259c31b3a64ee6903326d73"
AUTHORIZED_CONFIG_SHA = (
    "e252f1ba7beb577f0beb90bc9de294a16a8b808508081bb5b081b530fcaab460"
)
AUTHORIZED_WEIGHT_SHA = (
    "13e8d0ca250839500b71b4b9e23d8238a90488987b9a49cd2c6d2fc336f77fc6"
)
AUTHORIZED_AUTH_SHA = (
    "6341d0831327bdc3c912b133025b7265c62986badf369819d44dcaf506da42ed"
)
ANNOTATION_SHA = (
    "95d5436555da33ef7aaccf4c32194c29f00caced9a17adf2d2f65f12db7dc1fc"
)
EXCLUSION_SHA = (
    "661c9edb095f7f7dc28a24256b42e0a2796f9ab78fbabc24b23cf9bd57b06d69"
)
ANNOTATIONS = SURFACE / "FACTORIZED_ANNOTATIONS.jsonl"
OBJECTIVE_RECEIPT_SHA = (
    "45746d706d819da41eb56e788f13f4a873f8dc136c0057c9fa238a53b5bacfdc"
)
FILTER_RECEIPT_SHA = (
    "e8e2ab7f6773717ea94743a36084eae3f775d907936fadbe07d1c457bdd82ca3"
)
PARENT_DATASET_SHA = (
    "4095036e5af3ad7cfe9f038dd3e1f46e4ef0ea18db4c4b7186fc2b02e96d4274"
)
AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-ident-filtered-factorized-train-v1-20261001"
)
AUTH_FILE = AUTH_DEST / "AUTHORIZATION.json"
RESOLVED = AUTH_DEST / "RESOLVED_TRAINING_CONFIG.json"
WEIGHTS = AUTH_DEST / "IDENT_FILTERED_FACTORIZED_CLASS_WEIGHTS.json"
RUN_ROOT = AUTH_DEST / "classification-v5-stage-a-ident-filtered-factorized-001"
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
    "hyperlex-encoder-modernbert-base-seed-classification-v5-stage-a-ident-filtered-factorized-001"
)
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001"
)
SPEC_DIR = REPO / "specs" / "007-hyperlexical-model"

LITERAL_RELATION = {
    "NO_EVIDENCE_RELATION": 0.8985774732156429,
    "EVIDENCE_RELATION_PRESENT": 1.1014225267843571,
}
LITERAL_RESOLVABILITY = {
    "UNRESOLVABLE": 1.7030222347950057,
    "RESOLVABLE": 0.5,
}
SURFACE_RECEIPT_SHA = FILTER_RECEIPT_SHA
STAGE_A_BEST_SHA = (
    "cd2829c1b5fb823fc03f18efe66a7387124ef44be2545b9e385a17eb6237bf5c"
)
PARENT_DISJOINTNESS = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-generalization-surface-v1r1-20261001/"
    "DISJOINTNESS_WITNESS.json"
)

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
    from hyperlexical.classification_v5_stage_a_ident_filtered_authorize import (
        AUTHORIZE_RULE,
        AUTHORIZED_AUTH_RECEIPT_SHA256,
        AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
        AUTHORIZED_TRAINING_CONFIG_SHA256,
        EXPECTED_TRAIN_IDENTITY_LIST_SHA256,
        EXPECTED_TRAIN_ROWS,
        EXPECTED_TRAIN_SPLIT_SHA256,
        EXPECTED_VALIDATION_IDENTITY_LIST_SHA256,
        EXPECTED_VALIDATION_ROWS,
        EXPECTED_VALIDATION_SPLIT_SHA256,
        EXPERIMENT_ID,
        INITIALIZATION_POLICY,
        LITERAL_RELATION_WEIGHTS,
        LITERAL_RESOLVABILITY_WEIGHTS,
        verify_exclusion_integrity,
        verify_v1r2_split_pins,
    )
    from hyperlexical.classification_v5_stage_a_factorized_objective import (
        OBJECTIVE_ID,
        OBJECTIVE_RECEIPT_SHA256_PIN,
    )
    from hyperlexical.classification_v5_stage_a_gold_identifiability_filter import (
        FILTER_RECEIPT_SHA256_PIN,
        V1R2_ANNOTATION_SHA256_PIN,
        V1R2_DATASET_SHA256_PIN,
        V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
    )
    from hyperlexical.classification_v5_stage_a_two_stage import (
        identity_list_sha256,
        split_lines_sha256,
    )
    from hyperlexical.classification_v5_stage_a_two_stage_generalization import (
        PARENT_STAGE_A_BEST_SHA,
        SPENT_RESERVE_OVERLAP,
    )
    from hyperlexical.classification_v5_stage_a import BEST_SHA as AUTHORIZED_BEST_SHA

    if not AUTH_FILE.exists() or not RESOLVED.exists() or not WEIGHTS.exists():
        fail("authorization artifacts missing; run authorize first")
    if not ANNOTATIONS.exists():
        fail("v1r2 factorized annotations missing")
    if not EXCLUSION.exists():
        fail("exclusion manifest missing")
    auth = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    resolved = json.loads(RESOLVED.read_text(encoding="utf-8"))
    weights = json.loads(WEIGHTS.read_text(encoding="utf-8"))
    init_policy = json.loads(
        (AUTH_DEST / "INITIALIZATION_POLICY.json").read_text(encoding="utf-8")
    )
    dataset_sha = sha256_file(DATASET)
    annotation_sha = sha256_file(ANNOTATIONS)
    exclusion_sha = sha256_file(EXCLUSION)
    current_best = sudo_sha256(BEST_WEIGHTS)

    if auth.get("receipt_sha256") != AUTHORIZED_AUTH_RECEIPT_SHA256:
        fail(f"auth_receipt_mismatch:{auth.get('receipt_sha256')}")
    if auth.get("receipt_sha256") != AUTHORIZED_AUTH_SHA:
        fail("auth_receipt_local_pin_mismatch")
    if dataset_sha != V1R2_DATASET_SHA256_PIN or dataset_sha != DATASET_SHA:
        fail(f"dataset not authorized:{dataset_sha}")
    if annotation_sha != V1R2_ANNOTATION_SHA256_PIN or annotation_sha != ANNOTATION_SHA:
        fail(f"annotation not authorized:{annotation_sha}")
    if exclusion_sha != V1R2_EXCLUSION_MANIFEST_SHA256_PIN or exclusion_sha != EXCLUSION_SHA:
        fail(f"exclusion not authorized:{exclusion_sha}")
    if auth.get("SURFACE_RECEIPT_SHA256") != FILTER_RECEIPT_SHA256_PIN:
        fail("surface_receipt mismatch")
    if auth.get("SURFACE_RECEIPT_SHA256") != SURFACE_RECEIPT_SHA:
        fail("surface_receipt local pin mismatch")
    if auth.get("FILTER_RECEIPT_SHA256") != FILTER_RECEIPT_SHA:
        fail("filter_receipt local pin mismatch")
    if auth.get("ANNOTATION_SHA256") != ANNOTATION_SHA:
        fail("annotation local pin mismatch")
    if auth.get("EXCLUSION_MANIFEST_SHA256") != EXCLUSION_SHA:
        fail("exclusion local pin mismatch")
    if auth.get("PARENT_DATASET_SHA256") != PARENT_DATASET_SHA:
        fail("parent_dataset_sha mismatch")
    if auth.get("OBJECTIVE_RECEIPT_SHA256") != OBJECTIVE_RECEIPT_SHA256_PIN:
        fail("objective_receipt mismatch")
    if auth.get("OBJECTIVE_RECEIPT_SHA256") != OBJECTIVE_RECEIPT_SHA:
        fail("objective_receipt local pin mismatch")
    if resolved.get("training_config_sha256") != AUTHORIZED_TRAINING_CONFIG_SHA256:
        fail("resolved training_config_sha256 mismatch")
    if auth.get("TRAINING_CONFIG_SHA256") != AUTHORIZED_CONFIG_SHA:
        fail("auth training_config_sha256 mismatch")
    if weights.get("CLASS_WEIGHT_ARTIFACT_SHA256") != AUTHORIZED_WEIGHT_SHA:
        fail("class_weight_artifact_sha mismatch")
    if auth.get("CLASS_WEIGHT_ARTIFACT_SHA256") != AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256:
        fail("auth class_weight_artifact_sha mismatch")
    if auth.get("EXPERIMENT_ID") != EXPERIMENT_ID:
        fail(f"unexpected experiment:{auth.get('EXPERIMENT_ID')}")
    if auth.get("AUTHORIZE_RULE") != AUTHORIZE_RULE:
        fail(f"unexpected authorize_rule:{auth.get('AUTHORIZE_RULE')}")
    if auth.get("OBJECTIVE_ID") != OBJECTIVE_ID:
        fail("objective_id mismatch")
    if auth.get("TRAINING_RUN_LIMIT") != 1:
        fail("training_run_limit_mismatch")
    if auth.get("TRAIN_AUTHORIZED") is not True:
        fail("train_not_authorized")
    if auth.get("TRAINING_STATUS") not in {
        "AUTHORIZED_NOT_STARTED",
        "RUNNING",
        "COMPLETE",
    }:
        fail(f"unexpected_training_status:{auth.get('TRAINING_STATUS')}")
    if resolved.get("relation_class_weights_literal") != LITERAL_RELATION_WEIGHTS:
        fail("relation literal weights mismatch")
    if resolved.get("resolvability_class_weights_literal") != LITERAL_RESOLVABILITY_WEIGHTS:
        fail("resolvability literal weights mismatch")
    if weights.get("literal_weights", {}).get("relation") != LITERAL_RELATION:
        fail("weight artifact relation literal mismatch")
    if weights.get("literal_weights", {}).get("resolvability") != LITERAL_RESOLVABILITY:
        fail("weight artifact resolvability literal mismatch")
    if weights.get("reused_prior_factorized_weights") is not False:
        fail("prior_factorized_weights_reuse_forbidden")
    if current_best != AUTHORIZED_BEST_SHA or current_best != BEST_SHA:
        fail("MODEL_WIDE_BEST weights changed")
    if auth.get("CURRENT_STAGE_A_BEST") != PARENT_STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST mismatch")
    if auth.get("CURRENT_STAGE_A_BEST") != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST local pin mismatch")
    if auth.get("spent_reserve_overlap", SPENT_RESERVE_OVERLAP) != 0:
        fail("spent_reserve_overlap_nonzero")
    if auth.get("spent_reserve_access_for_train_val_select_threshold_diag") is not False:
        fail("spent_reserve_access_forbidden")
    if init_policy.get("stage_a_best_continuation") is not False:
        fail("initialization_policy_continuation_forbidden")
    if init_policy.get("base_encoder_sha256") != BEST_SHA:
        fail("initialization_policy_base_encoder_mismatch")
    if INITIALIZATION_POLICY["stage_a_best_continuation"] is not False:
        fail("module_initialization_policy_conflict")

    rows = load_jsonl(DATASET)
    annotations = load_jsonl(ANNOTATIONS)
    exclusion_rows = load_jsonl(EXCLUSION)
    ann_by_id = {str(a["identity"]): a for a in annotations}
    if len(ann_by_id) != len(annotations):
        fail("duplicate_annotation_identities")
    if len(annotations) != len(rows):
        fail("annotation_count_mismatch")

    excl_ids = [str(r["identity"]) for r in exclusion_rows]
    excl_integrity = verify_exclusion_integrity(
        v1r2_identities=[str(r["identity"]) for r in rows],
        exclusion_identities=excl_ids,
    )
    if not excl_integrity["pass"]:
        fail(f"exclusion_integrity_failed:{excl_integrity}")

    train_rows = [row for row in rows if row.get("split") == "train"]
    val_rows = [row for row in rows if row.get("split") == "validation"]
    train_split_sha = split_lines_sha256(str(DATASET), split="train")
    val_split_sha = split_lines_sha256(str(DATASET), split="validation")
    train_id_sha = identity_list_sha256([r["identity"] for r in train_rows])
    val_id_sha = identity_list_sha256([r["identity"] for r in val_rows])
    split_pin = verify_v1r2_split_pins(
        train_rows=train_rows,
        validation_rows=val_rows,
        train_split_sha256=train_split_sha,
        validation_split_sha256=val_split_sha,
        train_identity_list_sha256=train_id_sha,
        validation_identity_list_sha256=val_id_sha,
    )
    if not split_pin["pass"]:
        fail(f"split_pin_failed:{split_pin}")
    if train_id_sha != EXPECTED_TRAIN_IDENTITY_LIST_SHA256:
        fail("train_identity_mismatch")
    if val_id_sha != EXPECTED_VALIDATION_IDENTITY_LIST_SHA256:
        fail("val_identity_mismatch")
    if train_split_sha != EXPECTED_TRAIN_SPLIT_SHA256:
        fail("train_split_mismatch")
    if val_split_sha != EXPECTED_VALIDATION_SPLIT_SHA256:
        fail("val_split_mismatch")
    if len(train_rows) != EXPECTED_TRAIN_ROWS or len(val_rows) != EXPECTED_VALIDATION_ROWS:
        fail("split_count_mismatch")

    excluded_set = set(excl_ids)
    for row in rows:
        if str(row["identity"]) not in ann_by_id:
            fail(f"missing_annotation:{row['identity']}")
        if str(row["identity"]) in excluded_set:
            fail(f"excluded_identity_in_surface:{row['identity']}")

    if PARENT_DISJOINTNESS.exists():
        parent_disj = json.loads(PARENT_DISJOINTNESS.read_text(encoding="utf-8"))
        if parent_disj.get("pass") is not True:
            fail("parent_disjointness_fail")

    return {
        "auth": auth,
        "resolved": resolved,
        "weights": weights,
        "rows": rows,
        "train_rows": train_rows,
        "val_rows": val_rows,
        "annotations": ann_by_id,
        "exclusion_ids": excl_ids,
        "dataset_sha": dataset_sha,
        "annotation_sha": annotation_sha,
        "exclusion_sha": exclusion_sha,
        "train_split_sha": train_split_sha,
        "val_split_sha": val_split_sha,
        "train_id_sha": train_id_sha,
        "val_id_sha": val_id_sha,
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
    import math
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file, save_file

    from hyperlexical.classification_v5_stage_a import (
        TRAIN_HYPERPARAMS,
        canonical_json,
        evaluate_decisions,
        sha256_text,
    )
    from hyperlexical.classification_v5_stage_a_factorized_authorize import (
        calibrate_factorized_thresholds,
        checkpoint_selection_score,
        decide_stage_a,
        select_factorized_checkpoint,
    )
    from hyperlexical.classification_v5_stage_a_ident_filtered_authorize import (
        EXPERIMENT_ID,
        EXPECTED_OPTIMIZER_STEPS_PER_EPOCH,
        EXPECTED_TRAIN_ROWS,
        EXPLICIT_LIMITATIONS,
        IDENTIFIABILITY_DIAGNOSTIC_CONTRACT,
        INITIALIZATION_POLICY,
        SHORT_ATOM_POSITIVE_GENERALIZATION,
        TRAIN_ONCE_ACTION,
        TRAIN_RULE,
        build_v1r2_ident_filtered_split_witness,
    )
    from hyperlexical.classification_v5_stage_a_factorized_objective import (
        LAMBDA_RESOLVABILITY,
        MASKED,
        RELATION_LABELS,
        RESOLVABILITY_LABELS,
    )
    from hyperlexical.classification_v5_stage_a_two_stage import (
        DROP_LAST,
        binary_macro_f1,
        full_pass_batch_indices,
    )
    from hyperlexical.classification_v5_stage_a_two_stage_generalization import (
        AUTHORIZED_BEST_SHA,
        PARENT_STAGE_A_BEST_SHA,
        SPENT_RESERVE,
        SPENT_RESERVE_STATUS,
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
    ann_by_id = pins["annotations"]
    train_rows = pins["train_rows"]
    val_rows = pins["val_rows"]

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

    witness = build_v1r2_ident_filtered_split_witness(
        rows,
        dataset_sha256=pins["dataset_sha"],
        dataset_path=str(DATASET),
        code_revision=str(resolved.get("code_revision") or ""),
        exclusion_identities=pins["exclusion_ids"],
    )
    write_private(RUN_ROOT / "V1R2_IDENT_FILTERED_SPLIT_WITNESS.json", witness)
    write_private(AUTH_DEST / "V1R2_IDENT_FILTERED_SPLIT_WITNESS.json", witness)

    if len(train_rows) != EXPECTED_TRAIN_ROWS:
        fail("train_rows_mismatch_after_witness")
    if int(witness["optimizer_steps_per_epoch"]) != EXPECTED_OPTIMIZER_STEPS_PER_EPOCH:
        fail("optimizer_steps_per_epoch_mismatch")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("Stage A ident-filtered factorized train requires CUDA")

    if os.environ.get("HLX_V5_LOAD_STAGE_A_BEST") == "1":
        fail("STAGE_A_BEST_load_forbidden_for_ident_filtered_retrain")
    if INITIALIZATION_POLICY["stage_a_best_continuation"] is not False:
        fail("initialization_policy_forbids_continuation")

    seed = int(TRAIN_HYPERPARAMS["seed"])
    torch.manual_seed(seed)
    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    warm = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    if sudo_sha256(BEST_WEIGHTS) != AUTHORIZED_BEST_SHA:
        fail("MODEL_WIDE_BEST digest drifted before overlay")
    loaded = apply_encoder_trainable(encoder, warm.get("encoder") or {})
    if loaded["loaded"] != 48:
        fail(f"BEST encoder overlay missed tensors: loaded={loaded['loaded']}")
    trainable_params, last_n = freeze_encoder(
        encoder, last_trainable=int(TRAIN_HYPERPARAMS["last_trainable"])
    )
    relation_head = nn.Linear(HIDDEN, 2)
    resolvability_head = nn.Linear(HIDDEN, 2)
    nn.init.xavier_uniform_(relation_head.weight)
    nn.init.zeros_(relation_head.bias)
    nn.init.xavier_uniform_(resolvability_head.weight)
    nn.init.zeros_(resolvability_head.bias)

    write_private(
        RUN_ROOT / "INITIAL_CHECKPOINT.json",
        {
            "checkpoint_role": "INITIAL",
            "dataset_sha256": pins["dataset_sha"],
            "annotation_sha256": ANNOTATION_SHA,
            "heads": ["relation_head", "resolvability_head"],
            "head_init": TRAIN_HYPERPARAMS["head_init"],
            "initialization_policy": INITIALIZATION_POLICY,
            "parent_BEST_sha256": AUTHORIZED_BEST_SHA,
            "parent_STAGE_A_BEST_sha256_reference_only": PARENT_STAGE_A_BEST_SHA,
            "schema": (
                "hyperlex.classification.v5."
                "stage_a_ident_filtered_factorized_checkpoint_manifest.v1"
            ),
            "seed": seed,
            "stage_a_best_continuation": False,
            "training_config_sha256": resolved["training_config_sha256"],
        },
    )

    encoder.to(device)
    relation_head.to(device)
    resolvability_head.to(device)
    params = [
        p
        for p in list(encoder.parameters())
        + list(relation_head.parameters())
        + list(resolvability_head.parameters())
        if p.requires_grad
    ]
    optimizer = torch.optim.AdamW(
        params,
        lr=float(TRAIN_HYPERPARAMS["learning_rate"]),
        weight_decay=float(TRAIN_HYPERPARAMS["weight_decay"]),
    )

    rel_w = torch.tensor(
        [float(LITERAL_RELATION[label]) for label in RELATION_LABELS],
        dtype=torch.float32,
        device=device,
    )
    res_w = torch.tensor(
        [float(LITERAL_RESOLVABILITY[label]) for label in RESOLVABILITY_LABELS],
        dtype=torch.float32,
        device=device,
    )
    loss_rel = nn.CrossEntropyLoss(weight=rel_w, reduction="none")
    loss_res = nn.CrossEntropyLoss(weight=res_w, reduction="none")
    prov_mult = {"OBSERVED": 1.0, "INFERRED": 0.5}

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
        scale = float(step + 1) / float(warmup_steps) if step < warmup_steps else 1.0
        for group in optimizer.param_groups:
            group["lr"] = base_lr * scale

    def softmax2(logits):
        import torch.nn.functional as F
        return F.softmax(torch.tensor(logits, dtype=torch.float32), dim=-1).tolist()

    def score_split(split_rows: list[dict]):
        encoder.eval()
        relation_head.eval()
        resolvability_head.eval()
        golds, p_rel, p_res = [], [], []
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
                rel_probs = softmax2(relation_head(pooled)[0].detach().cpu().tolist())
                res_probs = softmax2(resolvability_head(pooled)[0].detach().cpu().tolist())
                golds.append(str(row["evidence_label"]))
                p_rel.append(float(rel_probs[1]))  # EVIDENCE_RELATION_PRESENT
                p_res.append(float(res_probs[1]))  # RESOLVABLE
        return golds, p_rel, p_res

    def capture_weights():
        return {
            "encoder": {
                k: v.detach().cpu().clone()
                for k, v in collect_encoder_trainable(encoder).items()
            },
            "relation_bias": relation_head.bias.detach().cpu().clone(),
            "relation_weight": relation_head.weight.detach().cpu().clone(),
            "resolvability_bias": resolvability_head.bias.detach().cpu().clone(),
            "resolvability_weight": resolvability_head.weight.detach().cpu().clone(),
        }

    def save_tmp_checkpoint(epoch: int, role: str, state: dict) -> Path:
        path = tmp_ckpt_root / f"checkpoint-{epoch:04d}-{role}"
        path.mkdir(parents=True, exist_ok=True)
        flat = flatten_weight_tensors(
            {
                "encoder": state["encoder"],
                "relation_head": {
                    "weight": state["relation_weight"].contiguous(),
                    "bias": state["relation_bias"].contiguous(),
                },
                "resolvability_head": {
                    "weight": state["resolvability_weight"].contiguous(),
                    "bias": state["resolvability_bias"].contiguous(),
                },
            }
        )
        save_file(flat, str(path / "model.safetensors"))
        write_private(path / "meta.json", {"epoch": epoch, "role": role, "temporary": True})
        return path

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

    for epoch in range(max_epochs):
        encoder.train()
        relation_head.train()
        resolvability_head.train()
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
            rel_targets = []
            rel_mask = []
            res_targets = []
            sample_w = []
            for i in batch_indices:
                row = train_rows[i]
                ann = ann_by_id[str(row["identity"])]
                res_targets.append(int(ann["semantic_resolvable"]))
                sample_w.append(float(prov_mult.get(str(row.get("provenance")), 0.5)))
                rel = ann["evidence_relation_present"]
                if rel == MASKED:
                    rel_targets.append(0)
                    rel_mask.append(0.0)
                else:
                    rel_targets.append(int(rel))
                    rel_mask.append(1.0)
            rel_targets_t = torch.tensor(rel_targets, dtype=torch.long, device=device)
            res_targets_t = torch.tensor(res_targets, dtype=torch.long, device=device)
            rel_mask_t = torch.tensor(rel_mask, dtype=torch.float32, device=device)
            sample_w_t = torch.tensor(sample_w, dtype=torch.float32, device=device)
            encoded = tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=max_len,
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            logits_rel = relation_head(pooled)
            logits_res = resolvability_head(pooled)
            per_res = loss_res(logits_res, res_targets_t) * sample_w_t
            l_res = per_res.mean()
            if float(rel_mask_t.sum().item()) > 0:
                per_rel = loss_rel(logits_rel, rel_targets_t) * sample_w_t * rel_mask_t
                l_rel = per_rel.sum() / rel_mask_t.sum()
            else:
                l_rel = torch.zeros((), device=device)
            loss = l_rel + float(LAMBDA_RESOLVABILITY) * l_res
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

        val_golds, val_pr, val_ps = score_split(val_rows)
        sel_rel_thr = 0.50
        sel_res_thr = 0.50
        # Relation macro-F1 on relation-eligible validation rows only.
        rel_idx = []
        rel_gold = []
        rel_pred = []
        for i, row in enumerate(val_rows):
            ann = ann_by_id[str(row["identity"])]
            if ann["evidence_relation_present"] == MASKED:
                continue
            rel_idx.append(i)
            rel_gold.append(int(ann["evidence_relation_present"]))
            rel_pred.append(1 if float(val_pr[i]) >= sel_rel_thr else 0)
        rel_macro = float(binary_macro_f1(rel_gold, rel_pred))
        res_gold = [int(ann_by_id[str(r["identity"])]["semantic_resolvable"]) for r in val_rows]
        res_pred = [1 if float(ps) >= sel_res_thr else 0 for ps in val_ps]
        res_macro = float(binary_macro_f1(res_gold, res_pred))
        sel_score = checkpoint_selection_score(
            relation_macro_f1=rel_macro, resolvability_macro_f1=res_macro
        )
        # Relation FPR among gold relation-negative eligible rows.
        neg_idx = [i for i, g in zip(rel_idx, rel_gold) if g == 0]
        if neg_idx:
            rel_fpr = sum(1 for i in neg_idx if float(val_pr[i]) >= sel_rel_thr) / len(neg_idx)
        else:
            rel_fpr = 0.0
        pos_idx = [i for i, g in zip(rel_idx, rel_gold) if g == 1]
        if pos_idx:
            rel_pos_recall = sum(1 for i in pos_idx if float(val_pr[i]) >= sel_rel_thr) / len(pos_idx)
        else:
            rel_pos_recall = 0.0
        unres_idx = [i for i, g in enumerate(res_gold) if g == 0]
        if unres_idx:
            unres_recall = sum(1 for i in unres_idx if float(val_ps[i]) < sel_res_thr) / len(unres_idx)
        else:
            unres_recall = 0.0

        cand = {
            "epoch": epoch + 1,
            "mean_train_loss": running / max(1, n_batches),
            "n_batches": n_batches,
            "optimizer_steps_cumulative": optimizer_steps,
            "relation_false_positive_rate": float(rel_fpr),
            "relation_macro_f1": rel_macro,
            "relation_positive_recall": float(rel_pos_recall),
            "resolvability_macro_f1": res_macro,
            "resolvability_unresolvable_recall": float(unres_recall),
            "selection_score": sel_score,
        }
        candidates.append(cand)
        epoch_trace.append(cand)
        with metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(cand) + "\n")
        print(json.dumps(cand, sort_keys=True), flush=True)

        chosen = select_factorized_checkpoint(candidates)
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

    apply_encoder_trainable(encoder, best_state["encoder"])
    with torch.no_grad():
        relation_head.weight.copy_(best_state["relation_weight"].to(device))
        relation_head.bias.copy_(best_state["relation_bias"].to(device))
        resolvability_head.weight.copy_(best_state["resolvability_weight"].to(device))
        resolvability_head.bias.copy_(best_state["resolvability_bias"].to(device))

    val_golds, val_pr, val_ps = score_split(val_rows)
    calibration = calibrate_factorized_thresholds(
        golds=val_golds, p_relation=val_pr, p_resolvable=val_ps
    )
    if not calibration["feasible"]:
        disposition = "SETTLED_FAIL"
        chosen_thr = {"relation_threshold": None, "resolvability_threshold": None}
        r_thr, s_thr = 0.50, 0.50
        promotion_candidate = False
    else:
        disposition = "SETTLED_PASS"
        chosen_thr = {
            "relation_threshold": calibration["chosen"]["relation_threshold"],
            "resolvability_threshold": calibration["chosen"]["resolvability_threshold"],
        }
        r_thr = float(chosen_thr["relation_threshold"])
        s_thr = float(chosen_thr["resolvability_threshold"])
        promotion_candidate = True

    val_decisions = [
        decide_stage_a(
            p_evidence_relation_present=float(pr),
            p_resolvable=float(ps),
            relation_threshold=r_thr,
            resolvability_threshold=s_thr,
        )
        for pr, ps in zip(val_pr, val_ps)
    ]
    val_metrics = evaluate_decisions(val_golds, val_decisions)
    if not val_metrics["acceptance_pass"]:
        disposition = "SETTLED_FAIL"
        promotion_candidate = False

    # SHORT_ATOM + identifiability diagnostics (V1R2 low-support PRESENT cohort).
    sa_none = [
        i
        for i, r in enumerate(val_rows)
        if r.get("primary_cell") == "SHORT_ATOM/NO_EVIDENCE"
    ]
    sa_pos = [
        i
        for i, r in enumerate(val_rows)
        if r.get("primary_cell") == "SHORT_ATOM/EVIDENCE_PRESENT"
    ]

    def _median(xs):
        if not xs:
            return None
        ys = sorted(xs)
        m = len(ys) // 2
        return ys[m] if len(ys) % 2 else 0.5 * (ys[m - 1] + ys[m])

    sa_none_dec = [val_decisions[i] for i in sa_none]
    sa_none_gold = [val_golds[i] for i in sa_none]
    sa_none_metrics = (
        evaluate_decisions(sa_none_gold, sa_none_dec) if sa_none else None
    )
    short_atom_diag = {
        "SHORT_ATOM_NONE": {
            "n": len(sa_none),
            "support": len(sa_none),
            "relation_false_positive_rate": (
                sum(1 for i in sa_none if float(val_pr[i]) >= r_thr) / len(sa_none)
                if sa_none
                else None
            ),
            "NONE_recall": (
                sa_none_metrics["by_label"]["NO_EVIDENCE"]["recall"]
                if sa_none_metrics
                else None
            ),
            "relation_score_median": _median([float(val_pr[i]) for i in sa_none]),
            "relation_score_mean": (
                sum(float(val_pr[i]) for i in sa_none) / len(sa_none)
                if sa_none
                else None
            ),
        },
        "SHORT_ATOM_PRESENT": {
            "n": len(sa_pos),
            "support": len(sa_pos),
            "relation_recall": (
                sum(1 for i in sa_pos if float(val_pr[i]) >= r_thr) / len(sa_pos)
                if sa_pos
                else None
            ),
            "low_support_warning": True,
            "stable_subgroup_guarantee": False,
            "SHORT_ATOM_POSITIVE_GENERALIZATION": SHORT_ATOM_POSITIVE_GENERALIZATION,
            "relation_score_median": _median([float(val_pr[i]) for i in sa_pos]),
            "relation_score_mean": (
                sum(float(val_pr[i]) for i in sa_pos) / len(sa_pos)
                if sa_pos
                else None
            ),
        },
        "contract": IDENTIFIABILITY_DIAGNOSTIC_CONTRACT,
    }
    # TEXT_IDENTIFIABLE / genuine UNCERTAIN / OBSERVED-INFERRED slices.
    text_ident_idx = [
        i
        for i, r in enumerate(val_rows)
        if ann_by_id[str(r["identity"])]["evidence_relation_present"] != MASKED
    ]
    uncertain_idx = [
        i
        for i, r in enumerate(val_rows)
        if ann_by_id[str(r["identity"])]["evidence_relation_present"] == MASKED
    ]
    identifiability_slices = {
        "TEXT_IDENTIFIABLE_relation_rows": {
            "n": len(text_ident_idx),
            **(
                {
                    k: evaluate_decisions(
                        [val_golds[i] for i in text_ident_idx],
                        [val_decisions[i] for i in text_ident_idx],
                    )[k]
                    for k in (
                        "stage_a_macro_f1",
                        "false_evidence_entry_rate_on_none",
                        "by_label",
                        "acceptance_pass",
                    )
                }
                if text_ident_idx
                else {}
            ),
        },
        "genuine_UNCERTAIN_rows": {
            "n": len(uncertain_idx),
            "UNCERTAIN_recall": (
                sum(1 for i in uncertain_idx if val_decisions[i] == "UNCERTAIN")
                / len(uncertain_idx)
                if uncertain_idx
                else None
            ),
        },
        "by_provenance": slice_diagnostics(
            val_rows,
            val_golds,
            val_decisions,
            key_fn=lambda r: r.get("provenance") or "UNKNOWN",
        ),
        "by_source_bucket": slice_diagnostics(
            val_rows, val_golds, val_decisions, key_fn=source_bucket
        ),
        "by_domain": slice_diagnostics(
            val_rows,
            val_golds,
            val_decisions,
            key_fn=lambda r: r.get("domain") or "UNKNOWN",
        ),
        "by_length_band": slice_diagnostics(
            val_rows, val_golds, val_decisions, key_fn=row_length_band
        ),
        "prior_factorized_read_only": IDENTIFIABILITY_DIAGNOSTIC_CONTRACT[
            "compare_read_only_prior_factorized"
        ],
    }

    selected_dir = RUN_ROOT / "selected"
    flat = flatten_weight_tensors(
        {
            "encoder": collect_encoder_trainable(encoder),
            "relation_head": {
                "weight": relation_head.weight.detach().cpu().contiguous(),
                "bias": relation_head.bias.detach().cpu().contiguous(),
            },
            "resolvability_head": {
                "weight": resolvability_head.weight.detach().cpu().contiguous(),
                "bias": resolvability_head.bias.detach().cpu().contiguous(),
            },
        }
    )
    selected_weights = selected_dir / "model.safetensors"
    save_file(flat, str(selected_weights))
    selected_config = {
        "BEST_MUTATED": False,
        "annotation_sha256": ANNOTATION_SHA,
        "class_weight_artifact_sha256": AUTHORIZED_WEIGHT_SHA,
        "code_revision": resolved.get("code_revision"),
        "dataset_sha256": pins["dataset_sha"],
        "experiment_id": EXPERIMENT_ID,
        "hidden_size": HIDDEN,
        "init_from": str(INIT_FROM),
        "last_trainable": last_n,
        "parent_BEST_sha256": AUTHORIZED_BEST_SHA,
        "pooling": TRAIN_HYPERPARAMS["pooling"],
        "promotion_candidate": promotion_candidate,
        "relation_threshold_selected": chosen_thr.get("relation_threshold"),
        "resolvability_threshold_selected": chosen_thr.get("resolvability_threshold"),
        "resolved_training_config_sha256": resolved["training_config_sha256"],
        "restored_epoch": best_epoch,
        "rule": TRAIN_RULE,
        "schema": (
            "hyperlex.classification.v5."
            "stage_a_ident_filtered_factorized_selected_config.v1"
        ),
        "seed": seed,
        "selection_score": best_record["selection_score"],
        "stage_a_best_continuation": False,
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
        },
    )

    OUT.mkdir(parents=True, exist_ok=True)
    os.chmod(OUT, 0o755)
    shutil.copy2(selected_weights, OUT / "model.safetensors")
    write_private(OUT / "stage_a_ident_filtered_factorized_config.json", selected_config)

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
        },
    )
    write_private(RUN_ROOT / "diagnostics" / "short_atom_relation.json", short_atom_diag)
    write_private(
        RUN_ROOT / "diagnostics" / "identifiability_slices.json",
        identifiability_slices,
    )
    write_private(
        RUN_ROOT / "diagnostics" / "by_length_band.json",
        identifiability_slices["by_length_band"],
    )
    write_private(
        RUN_ROOT / "diagnostics" / "by_provenance.json",
        identifiability_slices["by_provenance"],
    )
    write_private(
        RUN_ROOT / "diagnostics" / "by_source_bucket.json",
        identifiability_slices["by_source_bucket"],
    )
    write_private(
        RUN_ROOT / "diagnostics" / "by_domain.json",
        identifiability_slices["by_domain"],
    )

    next_action = (
        "PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE"
        if promotion_candidate
        else "DIAGNOSE_STAGE_A_IDENT_FILTERED_FACTORIZED_SETTLED_FAIL"
    )

    elapsed = time.time() - started
    receipt = {
        "AUTHORIZATION_RECEIPT_SHA256": AUTHORIZED_AUTH_SHA,
        "BEST_MUTATED": False,
        "CLASS_WEIGHT_ARTIFACT_SHA256": AUTHORIZED_WEIGHT_SHA,
        "DATASET_SHA256": pins["dataset_sha"],
        "ANNOTATION_SHA256": ANNOTATION_SHA,
        "EXCLUSION_MANIFEST_SHA256": EXCLUSION_SHA,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "FILTER_RECEIPT_SHA256": FILTER_RECEIPT_SHA,
        "MODEL_WIDE_BEST_MUTATED": False,
        "OBJECTIVE_ID": resolved.get("OBJECTIVE_ID"),
        "PARENT_DATASET_SHA256": PARENT_DATASET_SHA,
        "SCIENTIFIC_RESULT": disposition,
        "SELECTED_CHECKPOINT_SHA256": checkpoint_sha,
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_STATUS": SPENT_RESERVE_STATUS,
        "STAGE_A_BEST_MUTATED": False,
        "TRAINING_CONFIG_SHA256": resolved["training_config_sha256"],
        "TRAINING_STATUS": "COMPLETE",
        "V1R2_MUTATED": False,
        "acceptance_gates": acceptance_table,
        "elapsed_seconds": elapsed,
        "explicit_limitations": EXPLICIT_LIMITATIONS,
        "identifiability_slices": {
            "TEXT_IDENTIFIABLE_n": identifiability_slices[
                "TEXT_IDENTIFIABLE_relation_rows"
            ]["n"],
            "genuine_UNCERTAIN_n": identifiability_slices["genuine_UNCERTAIN_rows"][
                "n"
            ],
            "genuine_UNCERTAIN_recall": identifiability_slices[
                "genuine_UNCERTAIN_rows"
            ]["UNCERTAIN_recall"],
        },
        "n_threshold_passing": calibration["n_passing"],
        "promotion_candidate": promotion_candidate,
        "restored_epoch": best_epoch,
        "selected_thresholds": chosen_thr,
        "selection_score": best_record["selection_score"],
        "short_atom_relation_diagnostics": short_atom_diag,
        "validation_metrics": val_metrics,
        "DOMAIN_IRRELEVANT_GENERALIZATION": "NOT_ESTABLISHED",
        "SHORT_ATOM_POSITIVE_GENERALIZATION": SHORT_ATOM_POSITIVE_GENERALIZATION,
        "split_witness_sha256": witness["V1R2_IDENT_FILTERED_SPLIT_WITNESS_SHA256"],
    }
    receipt["RUN_RECEIPT_SHA256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "RUN_RECEIPT_SHA256"})
    )
    write_private(RUN_ROOT / "RUN_RECEIPT.json", receipt)

    summary = {
        **receipt,
        "TRAIN": True,
        "NEXT_ACTION": next_action,
        "epoch_trace": epoch_trace,
        "optimizer_steps": optimizer_steps,
        "TRAIN_ONCE_ACTION": TRAIN_ONCE_ACTION,
    }
    write_private(RUN_ROOT / "TRAIN_SUMMARY.json", summary)
    write_private(AUTH_DEST / "TRAIN_SUMMARY.json", summary)

    auth["TRAINING_STATUS"] = "COMPLETE"
    auth["SCIENTIFIC_RESULT"] = disposition
    auth["SELECTED_CHECKPOINT_SHA256"] = checkpoint_sha
    auth["NEXT_ACTION"] = next_action
    write_private(AUTH_FILE, auth)

    write_repo(REPO_ARTIFACTS / "train_once_summary.json", summary)
    public_receipt = {
        "AUTHORIZATION_RECEIPT_SHA256": AUTHORIZED_AUTH_SHA,
        "ANNOTATION_SHA256": ANNOTATION_SHA,
        "BEST": "UNCHANGED",
        "CLASS_WEIGHT_ARTIFACT_SHA256": AUTHORIZED_WEIGHT_SHA,
        "DATASET_SHA256": pins["dataset_sha"],
        "EXCLUSION_MANIFEST_SHA256": EXCLUSION_SHA,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "FILTER_RECEIPT_SHA256": FILTER_RECEIPT_SHA,
        "MODEL_WIDE_BEST_MUTATED": False,
        "OBJECTIVE_ID": resolved.get("OBJECTIVE_ID"),
        "PARENT_DATASET_SHA256": PARENT_DATASET_SHA,
        "RESERVE": SPENT_RESERVE_STATUS,
        "RUN_RECEIPT_SHA256": receipt["RUN_RECEIPT_SHA256"],
        "SCIENTIFIC_RESULT": disposition,
        "SELECTED_CHECKPOINT_SHA256": checkpoint_sha,
        "SPENT_RESERVE": SPENT_RESERVE,
        "STAGE_A_BEST_MUTATED": False,
        "TRAINING_CONFIG_SHA256": resolved["training_config_sha256"],
        "TRAINING_STATUS": "COMPLETE",
        "V1R2_MUTATED": False,
        "acceptance_gates": acceptance_table,
        "explicit_limitations": EXPLICIT_LIMITATIONS,
        "n_threshold_passing": calibration["n_passing"],
        "promotion_candidate": promotion_candidate,
        "restored_epoch": best_epoch,
        "selected_thresholds": chosen_thr,
        "selection_score": best_record["selection_score"],
        "short_atom_relation_diagnostics": {
            "SHORT_ATOM_NONE": short_atom_diag["SHORT_ATOM_NONE"],
            "SHORT_ATOM_PRESENT": short_atom_diag["SHORT_ATOM_PRESENT"],
        },
        "validation_metrics": {
            "stage_a_macro_f1": val_metrics["stage_a_macro_f1"],
            "false_evidence_entry_rate_on_none": val_metrics[
                "false_evidence_entry_rate_on_none"
            ],
            "by_label": val_metrics["by_label"],
            "acceptance_pass": val_metrics["acceptance_pass"],
        },
        "train": True,
        "DOMAIN_IRRELEVANT_GENERALIZATION": "NOT_ESTABLISHED",
        "SHORT_ATOM_POSITIVE_GENERALIZATION": SHORT_ATOM_POSITIVE_GENERALIZATION,
        "NEXT_ACTION": next_action,
    }
    write_repo(REPO_ARTIFACTS / "train_once_receipt.json", public_receipt)
    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-ident-filtered-factorized-train-once-receipt-20261001.json",
        public_receipt,
    )

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V5_STAGE_A_EXECUTE_IDENT_FILTERED_FACTORIZED_TRAIN") != "1":
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
                        "HLX_V5_STAGE_A_EXECUTE_IDENT_FILTERED_FACTORIZED_TRAIN=1 "
                        "to run the single train"
                    ),
                    "training_config_sha256": pins["resolved"]["training_config_sha256"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if os.environ.get("HLX_V5_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN_INNER") == "1":
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
        "HLX_V5_STAGE_A_EXECUTE_IDENT_FILTERED_FACTORIZED_TRAIN=1",
        "-e",
        "HLX_V5_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN_INNER=1",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v5_stage_a_ident_filtered_factorized_train.py"
        ),
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
