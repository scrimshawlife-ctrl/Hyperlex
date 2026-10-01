"""AUTHORIZE_STAGE_A_FACTORIZED_RELATION_TRAIN — Spark authorize runner.

Ordering (hard):
  1 verify V1R1 READY + pins + annotation SHA
  2 verify sealed split identity
  3 RESOLVE_STAGE_A_FACTORIZED_RELATION_CLASS_WEIGHTS (train only)
  4 seal FACTORIZED_RELATION_CLASS_WEIGHTS.json
  5 freeze initialization policy (fresh from MODEL_WIDE_BEST)
  6 seal RESOLVED_TRAINING_CONFIG.json
  7 create authorization receipt → TRAIN_AUTHORIZED=true

Does not train. Does not mutate V1R1/annotations. Does not move BEST.
Does not access spent reserve contents.
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
    "classification-v5-stage-a-generalization-surface-v1r1-20261001"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "4095036e5af3ad7cfe9f038dd3e1f46e4ef0ea18db4c4b7186fc2b02e96d4274"
READINESS_SHA = "c4b5fc0725b919c1dd11acfd575d594d8ddd76839836e5a3928f4d6c07030c96"
SURFACE_RECEIPT_SHA = (
    "3dbdd9b2cc30600698340f979d20a2c9b8559b9eafbbc24baf4fb1007e737fb9"
)
ANNOTATION_DIR = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-factorized-objective-v1-20261001"
)
ANNOTATIONS = ANNOTATION_DIR / "FACTORIZED_ANNOTATIONS.jsonl"
ANNOTATION_SHA = (
    "4ac884504e4b2fe27e0e5de159847a158c43e2c0d75832ddc5b5c657279778b6"
)
OBJECTIVE_RECEIPT_SHA = (
    "45746d706d819da41eb56e788f13f4a873f8dc136c0057c9fa238a53b5bacfdc"
)
AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-factorized-relation-train-v1-20261001"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
STAGE_A_BEST_SHA = (
    "cd2829c1b5fb823fc03f18efe66a7387124ef44be2545b9e385a17eb6237bf5c"
)
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-001"
)
SPEC_DIR = REPO / "specs" / "007-hyperlexical-model"
PUBLIC_OBJECTIVE_RECEIPT = (
    SPEC_DIR
    / "classification-v5-stage-a-factorized-objective-receipt-20261001.json"
)
PUBLIC_SURFACE_RECEIPT = (
    SPEC_DIR
    / "classification-v5-stage-a-generalization-surface-v1r1-receipt-20261001.json"
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


def split_lines_sha256(path: Path, *, split: str) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("split") == split:
                digest.update(line if line.endswith(b"\n") else line + b"\n")
    return digest.hexdigest()


def annotation_jsonl_sha256(path: Path) -> str:
    """Match sealed FACTORIZED_ANNOTATION_SHA256 (canonical sorted identities)."""
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text

    rows = load_jsonl(path)
    body = "".join(
        canonical_json(a) + "\n"
        for a in sorted(rows, key=lambda r: str(r["identity"]))
    )
    return sha256_text(body)


def code_revision() -> str:
    override = (os.environ.get("HLX_V5_STAGE_A_CODE_REVISION") or "").strip()
    if override:
        return override
    completed = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def main() -> int:
    from hyperlexical.classification_v5_stage_a import (
        attach_and_validate_label_provenance,
        canonical_json,
        sha256_text,
    )
    from hyperlexical.classification_v5_stage_a_factorized_authorize import (
        AUTHORIZE_RULE,
        EXPERIMENT_ID,
        INITIALIZATION_POLICY,
        TRAIN_ONCE_ACTION,
        TRAIN_RULE,
        factorized_authorization_contract,
        factorized_resolved_config,
        identity_list_sha256,
        resolve_factorized_relation_class_weights,
        verify_v1r1_split_pins,
    )
    from hyperlexical.classification_v5_stage_a_factorized_objective import (
        FACTORIZED_ANNOTATION_SHA256_PIN,
        OBJECTIVE_ID,
        OBJECTIVE_RECEIPT_SHA256_PIN,
    )
    from hyperlexical.classification_v5_stage_a_gold_label_mapping import (
        admission_invariants,
    )
    from hyperlexical.classification_v5_stage_a_two_stage_generalization import (
        AUTHORIZED_DATASET_SHA,
        AUTHORIZED_READINESS_SHA,
        AUTHORIZED_SURFACE_RECEIPT_SHA,
        AUTHORIZED_SURFACE_RULE,
        EXPECTED_TRAIN_IDENTITY_LIST_SHA256,
        EXPECTED_TRAIN_ROWS,
        EXPECTED_TRAIN_SPLIT_SHA256,
        EXPECTED_VALIDATION_IDENTITY_LIST_SHA256,
        EXPECTED_VALIDATION_ROWS,
        EXPECTED_VALIDATION_SPLIT_SHA256,
        PARENT_STAGE_A_BEST_SHA,
        SPENT_RESERVE,
        SPENT_RESERVE_OVERLAP,
        SPENT_RESERVE_STATUS,
    )

    if AUTHORIZED_DATASET_SHA != DATASET_SHA:
        fail("AUTHORIZED_DATASET_SHA pin mismatch")
    if FACTORIZED_ANNOTATION_SHA256_PIN != ANNOTATION_SHA:
        fail("annotation pin mismatch")
    if OBJECTIVE_RECEIPT_SHA256_PIN != OBJECTIVE_RECEIPT_SHA:
        fail("objective receipt pin mismatch")
    if AUTHORIZE_RULE != "AUTHORIZE_STAGE_A_FACTORIZED_RELATION_TRAIN":
        fail("AUTHORIZE_RULE pin mismatch")
    if EXPERIMENT_ID != "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-001":
        fail("EXPERIMENT_ID pin mismatch")
    if INITIALIZATION_POLICY["stage_a_best_continuation"] is not False:
        fail("initialization_policy_conflict:stage_a_best_continuation")
    if INITIALIZATION_POLICY["base_encoder_sha256"] != BEST_SHA:
        fail("initialization_policy_conflict:base_encoder")
    if PARENT_STAGE_A_BEST_SHA != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST pin mismatch")

    if not PUBLIC_OBJECTIVE_RECEIPT.is_file():
        fail(f"missing objective receipt:{PUBLIC_OBJECTIVE_RECEIPT}")
    sealed_obj = json.loads(PUBLIC_OBJECTIVE_RECEIPT.read_text(encoding="utf-8"))
    if sealed_obj.get("receipt_sha256") != OBJECTIVE_RECEIPT_SHA:
        fail("objective_receipt_field_mismatch")
    if sealed_obj.get("FACTORIZED_ANNOTATION_SHA256") != ANNOTATION_SHA:
        fail("objective_receipt_annotation_mismatch")
    if sealed_obj.get("OBJECTIVE_ID") != OBJECTIVE_ID:
        fail("objective_id mismatch")

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset digest mismatch")
    if sha256_file(SURFACE / "READINESS.json") != READINESS_SHA:
        fail("readiness digest mismatch")
    ann_sha = annotation_jsonl_sha256(ANNOTATIONS)
    if ann_sha != ANNOTATION_SHA:
        fail(f"annotation digest mismatch:{ann_sha}")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not TRUNK.exists():
        fail("tokenizer trunk missing")

    # Spent reserve must not be read for auth math — only ledger status constants.
    reserve_path = Path(
        "/home/morpheus/hlx-private/classification-v5-promotion-reserve-001"
    )
    if os.environ.get("HLX_V5_TOUCH_SPENT_RESERVE") == "1":
        fail("spent_reserve_access_forbidden")
    _ = (SPENT_RESERVE, SPENT_RESERVE_STATUS, SPENT_RESERVE_OVERLAP, reserve_path)

    readiness = json.loads((SURFACE / "READINESS.json").read_text(encoding="utf-8"))
    if readiness.get("state") != "READY" or not readiness.get("ready"):
        fail("surface readiness not READY")
    if readiness.get("surface_rule") != AUTHORIZED_SURFACE_RULE:
        fail("surface_rule mismatch")

    split_manifest = json.loads(
        (SURFACE / "SPLIT_MANIFEST.json").read_text(encoding="utf-8")
    )
    train_ids = list(split_manifest.get("train_identities") or [])
    val_ids = list(split_manifest.get("validation_identities") or [])
    if len(train_ids) != EXPECTED_TRAIN_ROWS or len(val_ids) != EXPECTED_VALIDATION_ROWS:
        fail("split_manifest_count_mismatch")

    rows = load_jsonl(DATASET)
    gold = admission_invariants(rows)
    if not gold.get("pass"):
        fail(f"LABEL_MAPPING_INVALID:{json.dumps(gold, sort_keys=True)[:500]}")
    provenance = attach_and_validate_label_provenance(rows)
    if not provenance["pass"] or provenance["invalid_provenance_rows"] != 0:
        fail(
            "LABEL_PROVENANCE_INVALID:"
            + json.dumps(provenance.get("invalid_samples", [])[:5], sort_keys=True)
        )

    annotations = load_jsonl(ANNOTATIONS)
    train_rows = [row for row in rows if row.get("split") == "train"]
    val_rows = [row for row in rows if row.get("split") == "validation"]
    train_split_sha = split_lines_sha256(DATASET, split="train")
    val_split_sha = split_lines_sha256(DATASET, split="validation")
    train_id_sha = identity_list_sha256(train_ids)
    val_id_sha = identity_list_sha256(val_ids)
    live_train_id_sha = identity_list_sha256([r["identity"] for r in train_rows])
    live_val_id_sha = identity_list_sha256([r["identity"] for r in val_rows])
    if live_train_id_sha != train_id_sha or live_val_id_sha != val_id_sha:
        fail("live_split_identity_mismatch_vs_manifest")

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
    if train_split_sha != EXPECTED_TRAIN_SPLIT_SHA256:
        fail("train_split_sha_mismatch")
    if val_split_sha != EXPECTED_VALIDATION_SPLIT_SHA256:
        fail("val_split_sha_mismatch")
    if train_id_sha != EXPECTED_TRAIN_IDENTITY_LIST_SHA256:
        fail("train_identity_sha_mismatch")
    if val_id_sha != EXPECTED_VALIDATION_IDENTITY_LIST_SHA256:
        fail("val_identity_sha_mismatch")

    revision = code_revision()
    weights = resolve_factorized_relation_class_weights(
        train_rows,
        annotations,
        dataset_sha256=DATASET_SHA,
        annotation_sha256=ANNOTATION_SHA,
        train_split_sha256=train_split_sha,
        train_identity_list_sha256=train_id_sha,
        code_revision=revision,
    )
    if weights["relation"]["coverage"]["n_eligible"] != (
        EXPECTED_TRAIN_ROWS - weights["relation"]["coverage"]["n_ambiguous"]
    ):
        fail("relation_eligible_accounting")
    if weights["resolvability"]["coverage"]["n_eligible"] != EXPECTED_TRAIN_ROWS:
        fail("resolvability_eligible_accounting")

    tokenizer_identity = f"local_files_only:{TRUNK.name}"
    resolved = factorized_resolved_config(
        dataset_sha256=DATASET_SHA,
        annotation_sha256=ANNOTATION_SHA,
        class_weight_artifact=weights,
        code_revision=revision,
        tokenizer_identity=tokenizer_identity,
        train_split_sha256=train_split_sha,
        validation_split_sha256=val_split_sha,
        train_identity_list_sha256=train_id_sha,
        validation_identity_list_sha256=val_id_sha,
        readiness_sha256=READINESS_SHA,
        surface_receipt_sha256=SURFACE_RECEIPT_SHA,
        objective_receipt_sha256=OBJECTIVE_RECEIPT_SHA,
    )
    auth = factorized_authorization_contract(
        dataset_sha256=DATASET_SHA,
        annotation_sha256=ANNOTATION_SHA,
        training_config_sha256=resolved["training_config_sha256"],
        class_weight_artifact_sha256=weights["CLASS_WEIGHT_ARTIFACT_SHA256"],
        code_revision=revision,
        readiness_sha256=READINESS_SHA,
        surface_receipt_sha256=SURFACE_RECEIPT_SHA,
        objective_receipt_sha256=OBJECTIVE_RECEIPT_SHA,
    )
    auth["INPUT_IDENTITY"] = "PASS"
    auth["SURFACE_READINESS"] = "PASS"
    auth["LABEL_MAPPING"] = "PASS"
    auth["SPLIT_IDENTITY"] = "PASS"
    auth["ANNOTATION_IDENTITY"] = "PASS"
    auth["authorized_surface_dir"] = str(SURFACE)
    auth["authorized_annotation_dir"] = str(ANNOTATION_DIR)
    auth["label_provenance_statistics"] = provenance["statistics"]
    auth["label_provenance_n_valid"] = provenance["n_valid"]
    auth["label_provenance_invalid"] = provenance["invalid_provenance_rows"]
    auth["split_pins"] = split_pin["expected"]
    auth["relation_class_weights_literal"] = resolved[
        "relation_class_weights_literal"
    ]
    auth["resolvability_class_weights_literal"] = resolved[
        "resolvability_class_weights_literal"
    ]
    auth["relation_eligible_train"] = weights["relation"]["coverage"]["n_eligible"]
    auth["relation_masked_train"] = weights["relation"]["coverage"]["n_masked"]
    auth["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in auth.items() if k != "receipt_sha256"})
    )

    if AUTH_DEST.exists() and (AUTH_DEST / "AUTHORIZATION.json").exists():
        fail(f"authorization already sealed:{AUTH_DEST}")

    AUTH_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(AUTH_DEST, 0o700)

    write_private(AUTH_DEST / "FACTORIZED_RELATION_CLASS_WEIGHTS.json", weights)
    write_private(AUTH_DEST / "RESOLVED_TRAINING_CONFIG.json", resolved)
    write_private(AUTH_DEST / "AUTHORIZATION.json", auth)
    write_private(AUTH_DEST / "INITIALIZATION_POLICY.json", INITIALIZATION_POLICY)
    write_private(AUTH_DEST / "SPLIT_PIN.json", split_pin)

    train_contract = {
        **resolved["acceptance_gates"],
        "annotation_sha256": ANNOTATION_SHA,
        "class_weight_artifact_sha256": weights["CLASS_WEIGHT_ARTIFACT_SHA256"],
        "contract_sha256": None,
        "experiment_id": EXPERIMENT_ID,
        "initialization_policy": INITIALIZATION_POLICY,
        "objective_id": OBJECTIVE_ID,
        "objective_receipt_sha256": OBJECTIVE_RECEIPT_SHA,
        "preregistered": True,
        "readiness_sha256": READINESS_SHA,
        "rule": TRAIN_RULE,
        "scope": "model_acceptance_after_authorized_factorized_relation_train",
        "spent_reserve": SPENT_RESERVE,
        "spent_reserve_overlap": SPENT_RESERVE_OVERLAP,
        "spent_reserve_status": SPENT_RESERVE_STATUS,
        "surface_dataset_sha256": DATASET_SHA,
        "surface_ready": True,
        "surface_receipt_sha256": SURFACE_RECEIPT_SHA,
        "train_authorized": True,
        "training_config_sha256": resolved["training_config_sha256"],
        "training_run_limit": 1,
        "training_status": "AUTHORIZED_NOT_STARTED",
    }
    train_contract["contract_sha256"] = sha256_text(
        canonical_json(
            {k: v for k, v in train_contract.items() if k != "contract_sha256"}
        )
    )
    write_private(
        AUTH_DEST / "STAGE_A_FACTORIZED_RELATION_TRAIN_CONTRACT.json",
        train_contract,
    )

    hashes = {}
    for path in sorted(AUTH_DEST.iterdir()):
        if path.is_file():
            hashes[path.name] = sha256_file(path)
    write_private(
        AUTH_DEST / "ARTIFACT_HASHES.json",
        {
            "files": hashes,
            "schema": (
                "hyperlex.classification.v5."
                "stage_a_factorized_relation_auth_hashes.v1"
            ),
        },
    )

    # Repo mirrors (no private text).
    REPO_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    for name in (
        "FACTORIZED_RELATION_CLASS_WEIGHTS.json",
        "RESOLVED_TRAINING_CONFIG.json",
        "AUTHORIZATION.json",
        "INITIALIZATION_POLICY.json",
        "STAGE_A_FACTORIZED_RELATION_TRAIN_CONTRACT.json",
        "ARTIFACT_HASHES.json",
    ):
        write_repo(REPO_ARTIFACTS / name, json.loads((AUTH_DEST / name).read_text()))

    spec_receipt = (
        SPEC_DIR
        / "classification-v5-stage-a-factorized-relation-authorize-receipt-20261001.json"
    )
    write_repo(spec_receipt, auth)

    summary = {
        "AUTHORIZE_RULE": AUTHORIZE_RULE,
        "CLASS_WEIGHT_ARTIFACT_SHA256": weights["CLASS_WEIGHT_ARTIFACT_SHA256"],
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "NEXT_ACTION": TRAIN_ONCE_ACTION,
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "TRAIN_AUTHORIZED": True,
        "TRAINING_CONFIG_SHA256": resolved["training_config_sha256"],
        "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
        "annotation_sha256": ANNOTATION_SHA,
        "auth_dest": str(AUTH_DEST),
        "dataset_sha256": DATASET_SHA,
        "receipt_sha256": auth["receipt_sha256"],
        "relation_eligible_train": weights["relation"]["coverage"]["n_eligible"],
        "relation_masked_train": weights["relation"]["coverage"]["n_masked"],
        "relation_weights": weights["literal_weights"]["relation"],
        "resolvability_weights": weights["literal_weights"]["resolvability"],
        "spec_receipt": str(spec_receipt),
        "train_split_sha256": train_split_sha,
        "validation_split_sha256": val_split_sha,
    }
    write_private(AUTH_DEST / "AUTHORIZATION_SUMMARY.json", summary)
    write_repo(REPO_ARTIFACTS / "authorization_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
