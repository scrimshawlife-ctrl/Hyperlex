"""AUTHORIZE_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN — Spark authorize.

Ordering:
  1 pin V1R2 / annotations / exclusion / filter receipt / objective
  2 exclusion integrity + parent split preservation
  3 RESOLVE_STAGE_A_IDENT_FILTERED_FACTORIZED_CLASS_WEIGHTS
  4 seal weights + resolved config + authorization
Does not train. Does not mutate V1R2. Does not restore excluded rows.
Does not move BEST. Does not access spent reserve contents.
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
DATASET_SHA = "492ed36751c7fdc40fe10bcdfabb69fa8783f8680259c31b3a64ee6903326d73"
ANNOTATION_SHA = (
    "95d5436555da33ef7aaccf4c32194c29f00caced9a17adf2d2f65f12db7dc1fc"
)
EXCLUSION_SHA = (
    "661c9edb095f7f7dc28a24256b42e0a2796f9ab78fbabc24b23cf9bd57b06d69"
)
FILTER_RECEIPT_SHA = (
    "e8e2ab7f6773717ea94743a36084eae3f775d907936fadbe07d1c457bdd82ca3"
)
OBJECTIVE_RECEIPT_SHA = (
    "45746d706d819da41eb56e788f13f4a873f8dc136c0057c9fa238a53b5bacfdc"
)
PARENT_DATASET_SHA = (
    "4095036e5af3ad7cfe9f038dd3e1f46e4ef0ea18db4c4b7186fc2b02e96d4274"
)
AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-ident-filtered-factorized-train-v1-20261001"
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
    / "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001"
)
SPEC_DIR = REPO / "specs" / "007-hyperlexical-model"
PUBLIC_FILTER_RECEIPT = (
    SPEC_DIR
    / "classification-v5-stage-a-gold-identifiability-filter-receipt-20261001.json"
)
PUBLIC_OBJECTIVE_RECEIPT = (
    SPEC_DIR
    / "classification-v5-stage-a-factorized-objective-receipt-20261001.json"
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
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v5_stage_a_factorized_objective import (
        MASKED,
        OBJECTIVE_ID,
        OBJECTIVE_RECEIPT_SHA256_PIN,
    )
    from hyperlexical.classification_v5_stage_a_gold_identifiability_filter import (
        FILTER_RECEIPT_SHA256_PIN,
        PARENT_DATASET_SHA256,
        V1R2_ANNOTATION_SHA256_PIN,
        V1R2_DATASET_SHA256_PIN,
        V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
    )
    from hyperlexical.classification_v5_stage_a_ident_filtered_authorize import (
        AUTHORIZE_RULE,
        EXPECTED_RELATION_ELIGIBLE_TOTAL,
        EXPECTED_RELATION_MASKED_TOTAL,
        EXPECTED_TRAIN_ROWS,
        EXPECTED_VALIDATION_ROWS,
        EXPERIMENT_ID,
        INITIALIZATION_POLICY,
        TRAIN_ONCE_ACTION,
        TRAIN_RULE,
        ident_filtered_authorization_contract,
        ident_filtered_resolved_config,
        resolve_ident_filtered_factorized_class_weights,
        verify_exclusion_integrity,
        verify_v1r2_split_pins,
    )
    from hyperlexical.classification_v5_stage_a_two_stage import identity_list_sha256
    from hyperlexical.classification_v5_stage_a_two_stage_generalization import (
        PARENT_STAGE_A_BEST_SHA,
        SPENT_RESERVE,
        SPENT_RESERVE_OVERLAP,
        SPENT_RESERVE_STATUS,
    )

    if V1R2_DATASET_SHA256_PIN != DATASET_SHA:
        fail("dataset pin mismatch")
    if V1R2_ANNOTATION_SHA256_PIN != ANNOTATION_SHA:
        fail("annotation pin mismatch")
    if V1R2_EXCLUSION_MANIFEST_SHA256_PIN != EXCLUSION_SHA:
        fail("exclusion pin mismatch")
    if FILTER_RECEIPT_SHA256_PIN != FILTER_RECEIPT_SHA:
        fail("filter receipt pin mismatch")
    if PARENT_DATASET_SHA256 != PARENT_DATASET_SHA:
        fail("parent dataset pin mismatch")
    if OBJECTIVE_RECEIPT_SHA256_PIN != OBJECTIVE_RECEIPT_SHA:
        fail("objective receipt pin mismatch")
    if AUTHORIZE_RULE != "AUTHORIZE_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN":
        fail("AUTHORIZE_RULE pin mismatch")
    if EXPERIMENT_ID != (
        "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001"
    ):
        fail("EXPERIMENT_ID pin mismatch")
    if INITIALIZATION_POLICY["stage_a_best_continuation"] is not False:
        fail("initialization_policy_conflict")
    if INITIALIZATION_POLICY["base_encoder_sha256"] != BEST_SHA:
        fail("initialization_policy_conflict:base_encoder")
    if PARENT_STAGE_A_BEST_SHA != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST pin mismatch")

    if not PUBLIC_FILTER_RECEIPT.is_file():
        fail(f"missing filter receipt:{PUBLIC_FILTER_RECEIPT}")
    sealed_filter = json.loads(PUBLIC_FILTER_RECEIPT.read_text(encoding="utf-8"))
    if sealed_filter.get("receipt_sha256") != FILTER_RECEIPT_SHA:
        fail("filter_receipt_field_mismatch")
    if sealed_filter.get("DATASET_SHA256") != DATASET_SHA:
        fail("filter_receipt_dataset_mismatch")
    if sealed_filter.get("FACTORIZED_ANNOTATION_SHA256") != ANNOTATION_SHA:
        fail("filter_receipt_annotation_mismatch")

    if not PUBLIC_OBJECTIVE_RECEIPT.is_file():
        fail(f"missing objective receipt:{PUBLIC_OBJECTIVE_RECEIPT}")
    sealed_obj = json.loads(PUBLIC_OBJECTIVE_RECEIPT.read_text(encoding="utf-8"))
    if sealed_obj.get("receipt_sha256") != OBJECTIVE_RECEIPT_SHA:
        fail("objective_receipt_field_mismatch")
    if sealed_obj.get("OBJECTIVE_ID") != OBJECTIVE_ID:
        fail("objective_id mismatch")

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset digest mismatch")
    if sha256_file(ANNOTATIONS) != ANNOTATION_SHA:
        fail("annotation digest mismatch")
    if sha256_file(EXCLUSION) != EXCLUSION_SHA:
        fail("exclusion digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not TRUNK.exists():
        fail("tokenizer trunk missing")

    if os.environ.get("HLX_V5_TOUCH_SPENT_RESERVE") == "1":
        fail("spent_reserve_access_forbidden")
    _ = (SPENT_RESERVE, SPENT_RESERVE_STATUS, SPENT_RESERVE_OVERLAP)

    rows = load_jsonl(DATASET)
    annotations = load_jsonl(ANNOTATIONS)
    excluded = load_jsonl(EXCLUSION)
    if len(annotations) != len(rows):
        fail("annotation_row_count_mismatch")
    ann_ids = {str(a["identity"]) for a in annotations}
    row_ids = [str(r["identity"]) for r in rows]
    if set(row_ids) != ann_ids:
        fail("annotation_identity_set_mismatch")

    excl_integrity = verify_exclusion_integrity(
        v1r2_identities=row_ids,
        exclusion_identities=[str(e["identity"]) for e in excluded],
    )

    # Overall relation eligibility totals
    from hyperlexical.classification_v5_stage_a_ident_filtered_authorize import (
        load_annotation_index,
    )

    ann_index = load_annotation_index(annotations)
    n_elig = 0
    n_mask = 0
    for row in rows:
        rel = ann_index[str(row["identity"])]["evidence_relation_present"]
        if rel == MASKED:
            n_mask += 1
        elif rel in (0, 1):
            n_elig += 1
        else:
            fail(f"bad_relation:{row['identity']}")
    if n_elig != EXPECTED_RELATION_ELIGIBLE_TOTAL or n_mask != EXPECTED_RELATION_MASKED_TOTAL:
        fail(f"relation_totals_mismatch:{n_elig}:{n_mask}")

    train_rows = [r for r in rows if r.get("split") == "train"]
    val_rows = [r for r in rows if r.get("split") == "validation"]
    train_split_sha = split_lines_sha256(DATASET, split="train")
    val_split_sha = split_lines_sha256(DATASET, split="validation")
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

    # Ensure excluded identities absent from train/val
    excl_set = {str(e["identity"]) for e in excluded}
    if any(str(r["identity"]) in excl_set for r in train_rows + val_rows):
        fail("excluded_identity_in_splits")

    revision = code_revision()
    weights = resolve_ident_filtered_factorized_class_weights(
        train_rows,
        annotations,
        dataset_sha256=DATASET_SHA,
        annotation_sha256=ANNOTATION_SHA,
        exclusion_manifest_sha256=EXCLUSION_SHA,
        train_split_sha256=train_split_sha,
        train_identity_list_sha256=train_id_sha,
        code_revision=revision,
    )

    tokenizer_identity = f"local_files_only:{TRUNK.name}"
    resolved = ident_filtered_resolved_config(
        dataset_sha256=DATASET_SHA,
        annotation_sha256=ANNOTATION_SHA,
        exclusion_manifest_sha256=EXCLUSION_SHA,
        class_weight_artifact=weights,
        code_revision=revision,
        tokenizer_identity=tokenizer_identity,
        train_split_sha256=train_split_sha,
        validation_split_sha256=val_split_sha,
        train_identity_list_sha256=train_id_sha,
        validation_identity_list_sha256=val_id_sha,
        surface_receipt_sha256=FILTER_RECEIPT_SHA,
        objective_receipt_sha256=OBJECTIVE_RECEIPT_SHA,
    )
    auth = ident_filtered_authorization_contract(
        dataset_sha256=DATASET_SHA,
        annotation_sha256=ANNOTATION_SHA,
        exclusion_manifest_sha256=EXCLUSION_SHA,
        training_config_sha256=resolved["training_config_sha256"],
        class_weight_artifact_sha256=weights["CLASS_WEIGHT_ARTIFACT_SHA256"],
        code_revision=revision,
        surface_receipt_sha256=FILTER_RECEIPT_SHA,
        objective_receipt_sha256=OBJECTIVE_RECEIPT_SHA,
    )
    auth["INPUT_IDENTITY"] = "PASS"
    auth["EXCLUSION_INTEGRITY"] = "PASS"
    auth["SPLIT_IDENTITY"] = "PASS"
    auth["ANNOTATION_IDENTITY"] = "PASS"
    auth["authorized_surface_dir"] = str(V1R2)
    auth["split_pins"] = split_pin["expected"]
    auth["exclusion_integrity"] = excl_integrity
    auth["relation_class_weights_literal"] = resolved[
        "relation_class_weights_literal"
    ]
    auth["resolvability_class_weights_literal"] = resolved[
        "resolvability_class_weights_literal"
    ]
    auth["relation_eligible_train"] = weights["relation"]["coverage"]["n_eligible"]
    auth["relation_masked_train"] = weights["relation"]["coverage"]["n_masked"]
    auth["V1R2_TRAIN_ROWS"] = EXPECTED_TRAIN_ROWS
    auth["V1R2_VALIDATION_ROWS"] = EXPECTED_VALIDATION_ROWS
    auth["V1R2_TRAIN_SPLIT_SHA256"] = train_split_sha
    auth["V1R2_VALIDATION_SPLIT_SHA256"] = val_split_sha
    auth["V1R2_TRAIN_IDENTITY_SHA256"] = train_id_sha
    auth["V1R2_VALIDATION_IDENTITY_SHA256"] = val_id_sha
    auth["RELATION_TRAIN_ELIGIBLE_COUNT"] = weights["relation"]["coverage"][
        "n_eligible"
    ]
    auth["RELATION_TRAIN_ELIGIBLE_ID_SHA256"] = weights["relation"][
        "eligible_identity_list_sha256"
    ]
    auth["RELATION_TRAIN_MASKED_COUNT"] = weights["relation"]["coverage"]["n_masked"]
    auth["RELATION_TRAIN_MASKED_ID_SHA256"] = weights["relation"][
        "masked_identity_list_sha256"
    ]
    auth["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in auth.items() if k != "receipt_sha256"})
    )

    if AUTH_DEST.exists() and (AUTH_DEST / "AUTHORIZATION.json").exists():
        fail(f"authorization already sealed:{AUTH_DEST}")
    AUTH_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(AUTH_DEST, 0o700)

    write_private(AUTH_DEST / "IDENT_FILTERED_FACTORIZED_CLASS_WEIGHTS.json", weights)
    write_private(AUTH_DEST / "RESOLVED_TRAINING_CONFIG.json", resolved)
    write_private(AUTH_DEST / "AUTHORIZATION.json", auth)
    write_private(AUTH_DEST / "INITIALIZATION_POLICY.json", INITIALIZATION_POLICY)
    write_private(AUTH_DEST / "SPLIT_PIN.json", split_pin)
    write_private(AUTH_DEST / "EXCLUSION_INTEGRITY.json", excl_integrity)

    train_contract = {
        **resolved["acceptance_gates"],
        "annotation_sha256": ANNOTATION_SHA,
        "class_weight_artifact_sha256": weights["CLASS_WEIGHT_ARTIFACT_SHA256"],
        "contract_sha256": None,
        "exclusion_manifest_sha256": EXCLUSION_SHA,
        "experiment_id": EXPERIMENT_ID,
        "initialization_policy": INITIALIZATION_POLICY,
        "objective_id": OBJECTIVE_ID,
        "objective_receipt_sha256": OBJECTIVE_RECEIPT_SHA,
        "preregistered": True,
        "rule": TRAIN_RULE,
        "scope": "model_acceptance_after_authorized_ident_filtered_factorized_train",
        "spent_reserve": SPENT_RESERVE,
        "spent_reserve_overlap": SPENT_RESERVE_OVERLAP,
        "spent_reserve_status": SPENT_RESERVE_STATUS,
        "surface_dataset_sha256": DATASET_SHA,
        "surface_receipt_sha256": FILTER_RECEIPT_SHA,
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
        AUTH_DEST / "STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN_CONTRACT.json",
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
                "stage_a_ident_filtered_factorized_auth_hashes.v1"
            ),
        },
    )

    REPO_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    for name in (
        "IDENT_FILTERED_FACTORIZED_CLASS_WEIGHTS.json",
        "RESOLVED_TRAINING_CONFIG.json",
        "AUTHORIZATION.json",
        "INITIALIZATION_POLICY.json",
        "STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN_CONTRACT.json",
        "ARTIFACT_HASHES.json",
        "SPLIT_PIN.json",
        "EXCLUSION_INTEGRITY.json",
    ):
        write_repo(REPO_ARTIFACTS / name, json.loads((AUTH_DEST / name).read_text()))

    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-ident-filtered-factorized-authorize-receipt-20261001.json",
        auth,
    )

    md = f"""# Classification v5 — Authorize ident-filtered factorized train

```text
RULE = {AUTHORIZE_RULE}
EXPERIMENT = {EXPERIMENT_ID}
SURFACE = V1R2 / {DATASET_SHA[:16]}…
ANNOTATIONS = {ANNOTATION_SHA[:16]}…
EXCLUSION = {EXCLUSION_SHA[:16]}…
FILTER_RECEIPT = {FILTER_RECEIPT_SHA[:16]}…
OBJECTIVE = {OBJECTIVE_ID}
TRAIN_AUTHORIZED = true
TRAINING_STATUS = AUTHORIZED_NOT_STARTED
TRAINING_RUN_LIMIT = 1
SCIENTIFIC_RESULT = NOT_COMPUTABLE
CLASS_WEIGHT_ARTIFACT = {weights['CLASS_WEIGHT_ARTIFACT_SHA256'][:16]}…
TRAINING_CONFIG = {resolved['training_config_sha256'][:16]}…
receipt = {auth['receipt_sha256'][:16]}…
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
NEXT_ACTION = {TRAIN_ONCE_ACTION}
```

Authorization only. No train. V1R2 unmodified. Excluded identities not restored.

## Splits (parent membership preserved)

| Split | n | split SHA | identity SHA |
|---|---:|---|---|
| train | {EXPECTED_TRAIN_ROWS} | {train_split_sha[:16]}… | {train_id_sha[:16]}… |
| validation | {EXPECTED_VALIDATION_ROWS} | {val_split_sha[:16]}… | {val_id_sha[:16]}… |

## Relation train eligibility

| Set | n | identity SHA |
|---|---:|---|
| eligible | {weights['relation']['coverage']['n_eligible']} | {weights['relation']['eligible_identity_list_sha256'][:16]}… |
| masked (UNCERTAIN) | {weights['relation']['coverage']['n_masked']} | {weights['relation']['masked_identity_list_sha256'][:16]}… |

## Class weights (train-only, fresh)

**Relation:** `{weights['literal_weights']['relation']}`

**Resolvability:** `{weights['literal_weights']['resolvability']}`

## Limitations

```text
DOMAIN_IRRELEVANT_GENERALIZATION = NOT_ESTABLISHED
SHORT_ATOM_POSITIVE_GENERALIZATION = LOW_SUPPORT (n_PRESENT=11)
MODEL_INPUT = text
```

Do **not** train until `TRAIN_STAGE_A_IDENT_FILTERED_FACTORIZED_ONCE` is explicitly executed.
"""
    (SPEC_DIR / "classification-v5-stage-a-ident-filtered-factorized-authorize-20261001.md").write_text(
        md, encoding="utf-8"
    )
    write_private(AUTH_DEST / "AUTHORIZATION.md", md)

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
        "exclusion_manifest_sha256": EXCLUSION_SHA,
        "receipt_sha256": auth["receipt_sha256"],
        "relation_eligible_train": weights["relation"]["coverage"]["n_eligible"],
        "relation_masked_train": weights["relation"]["coverage"]["n_masked"],
        "relation_weights": weights["literal_weights"]["relation"],
        "resolvability_weights": weights["literal_weights"]["resolvability"],
        "train_rows": EXPECTED_TRAIN_ROWS,
        "validation_rows": EXPECTED_VALIDATION_ROWS,
        "train_split_sha256": train_split_sha,
        "validation_split_sha256": val_split_sha,
    }
    write_private(AUTH_DEST / "AUTHORIZATION_SUMMARY.json", summary)
    write_repo(REPO_ARTIFACTS / "authorization_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
