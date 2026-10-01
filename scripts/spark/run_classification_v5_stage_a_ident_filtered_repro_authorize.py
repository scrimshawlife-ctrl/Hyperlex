"""AUTHORIZE_REPRODUCE_IDENT_FILTERED_FACTORIZED_TRAIN — Spark authorize.

Authorization only. Reuses sealed V1R2 + original class weights. Does not
train, recompute weights, mutate V1R2, move BEST, or score reserve.
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

V1R2 = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-identifiability-filtered-v1r2-20261001"
)
DATASET = V1R2 / "EVIDENCE_SURFACE.jsonl"
ANNOTATIONS = V1R2 / "FACTORIZED_ANNOTATIONS.jsonl"
EXCLUSION = V1R2 / "EXCLUSION_MANIFEST.jsonl"
PARENT_AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-ident-filtered-factorized-train-v1-20261001"
)
AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-ident-filtered-factorized-repro-v1-20261001"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
STAGE_A_BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/"
    "hyperlex-encoder-modernbert-base-seed-classification-v5-stage-a-two-stage-001/"
    "model.safetensors"
)
PARENT_PUBLIC_WEIGHTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001"
    / "IDENT_FILTERED_FACTORIZED_CLASS_WEIGHTS.json"
)
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-REPRO-001"
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
    from hyperlexical.classification_v5_stage_a import BEST_SHA, canonical_json, sha256_text
    from hyperlexical.classification_v5_stage_a_gold_identifiability_filter import (
        V1R2_ANNOTATION_SHA256_PIN,
        V1R2_DATASET_SHA256_PIN,
        V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
    )
    from hyperlexical.classification_v5_stage_a_ident_filtered_authorize import (
        AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
        EXPECTED_RELATION_TRAIN_ELIGIBLE_ID_SHA256,
        EXPECTED_RELATION_TRAIN_MASKED_ID_SHA256,
        EXPECTED_TRAIN_IDENTITY_LIST_SHA256,
        EXPECTED_VALIDATION_IDENTITY_LIST_SHA256,
    )
    from hyperlexical.classification_v5_stage_a_ident_filtered_repro_authorize import (
        AUTHORIZE_RULE,
        EXPERIMENT_ID,
        PARENT_EXPERIMENT,
        REPRODUCTION_REASON,
        TRAIN_ONCE_ACTION,
        authorize_reproduction,
    )
    from hyperlexical.classification_v5_stage_a_two_stage import identity_list_sha256
    from hyperlexical.classification_v5_stage_a_two_stage_generalization import (
        PARENT_STAGE_A_BEST_SHA,
    )

    if sha256_file(DATASET) != V1R2_DATASET_SHA256_PIN:
        fail("dataset digest mismatch")
    if sha256_file(ANNOTATIONS) != V1R2_ANNOTATION_SHA256_PIN:
        fail("annotation digest mismatch")
    if sha256_file(EXCLUSION) != V1R2_EXCLUSION_MANIFEST_SHA256_PIN:
        fail("exclusion digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("MODEL_WIDE_BEST mutated")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != PARENT_STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST mutated")
    if os.environ.get("HLX_V5_TOUCH_SPENT_RESERVE") == "1":
        fail("spent_reserve_access_forbidden")

    rows = load_jsonl(DATASET)
    train_rows = [r for r in rows if r.get("split") == "train"]
    val_rows = [r for r in rows if r.get("split") == "validation"]
    train_split_sha = split_lines_sha256(DATASET, split="train")
    val_split_sha = split_lines_sha256(DATASET, split="validation")
    train_id_sha = identity_list_sha256([r["identity"] for r in train_rows])
    val_id_sha = identity_list_sha256([r["identity"] for r in val_rows])

    if PARENT_PUBLIC_WEIGHTS.is_file():
        weights = json.loads(PARENT_PUBLIC_WEIGHTS.read_text(encoding="utf-8"))
    else:
        weights = json.loads(
            (PARENT_AUTH_DEST / "IDENT_FILTERED_FACTORIZED_CLASS_WEIGHTS.json").read_text(
                encoding="utf-8"
            )
        )
    if weights.get("CLASS_WEIGHT_ARTIFACT_SHA256") != AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256:
        fail("sealed_class_weights_sha_mismatch")

    revision = code_revision()
    bundle = authorize_reproduction(
        class_weight_artifact=weights,
        code_revision=revision,
        train_rows=len(train_rows),
        validation_rows=len(val_rows),
        train_split_sha256=train_split_sha,
        validation_split_sha256=val_split_sha,
        train_identity_sha256=train_id_sha,
        validation_identity_sha256=val_id_sha,
        relation_eligible_train_sha256=EXPECTED_RELATION_TRAIN_ELIGIBLE_ID_SHA256,
        relation_masked_train_sha256=EXPECTED_RELATION_TRAIN_MASKED_ID_SHA256,
    )
    auth = bundle["authorization"]
    config = bundle["training_config"]
    if auth["TRAIN_AUTHORIZED"] is not True:
        fail("not_authorized")
    if auth["NEXT_ACTION"] != TRAIN_ONCE_ACTION:
        fail("next_action_mismatch")

    if AUTH_DEST.exists() and (AUTH_DEST / "AUTHORIZATION.json").exists():
        fail(f"authorization already sealed:{AUTH_DEST}")
    AUTH_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(AUTH_DEST, 0o700)

    write_private(AUTH_DEST / "IDENT_FILTERED_FACTORIZED_CLASS_WEIGHTS.json", weights)
    write_private(AUTH_DEST / "RESOLVED_REPRODUCTION_TRAINING_CONFIG.json", config)
    write_private(AUTH_DEST / "AUTHORIZATION.json", auth)
    write_private(AUTH_DEST / "INITIALIZATION_POLICY.json", auth["initialization_policy"])
    write_private(AUTH_DEST / "SPLIT_IDENTITY.json", bundle["split_identity"])
    write_private(AUTH_DEST / "SCIENTIFIC_CONFIG_PARITY.json", bundle["scientific_parity"])
    write_private(AUTH_DEST / "RNG_CONTRACT.json", bundle["rng_contract"])
    write_private(
        AUTH_DEST / "SERIALIZATION_REGRESSION.json",
        bundle["serialization_regression_tests"],
    )

    REPO_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("AUTHORIZATION.json", auth),
        ("RESOLVED_REPRODUCTION_TRAINING_CONFIG.json", config),
        ("IDENT_FILTERED_FACTORIZED_CLASS_WEIGHTS.json", weights),
        ("SPLIT_IDENTITY.json", bundle["split_identity"]),
        ("SCIENTIFIC_CONFIG_PARITY.json", bundle["scientific_parity"]),
        ("RNG_CONTRACT.json", bundle["rng_contract"]),
        ("SERIALIZATION_REGRESSION.json", bundle["serialization_regression_tests"]),
    ):
        write_repo(REPO_ARTIFACTS / name, payload)
    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-ident-filtered-factorized-repro-authorize-receipt-20261001.json",
        auth,
    )
    summary = {
        "AUTHORIZE_RULE": AUTHORIZE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "PARENT_EXPERIMENT": PARENT_EXPERIMENT,
        "REPRODUCTION_REASON": REPRODUCTION_REASON,
        "NEXT_ACTION": TRAIN_ONCE_ACTION,
        "TRAIN_AUTHORIZED": True,
        "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
        "SCIENTIFIC_RESULT": "NOT_COMPUTABLE",
        "SCIENTIFIC_CONFIG_PARITY": auth["SCIENTIFIC_CONFIG_PARITY"],
        "REPRODUCTION_TRAINING_CONFIG_SHA256": config["training_config_sha256"],
        "receipt_sha256": auth["receipt_sha256"],
        "CLASS_WEIGHT_ARTIFACT_SHA256": AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
        "STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
        "MODEL_WIDE_BEST": BEST_SHA,
        "train_identity_list_sha256": train_id_sha,
        "validation_identity_list_sha256": val_id_sha,
    }
    write_private(AUTH_DEST / "AUTHORIZATION_SUMMARY.json", summary)
    write_repo(REPO_ARTIFACTS / "authorization_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    _ = sha256_text(canonical_json(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
