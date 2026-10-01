"""AUTHORIZE_V5_STAGE_A_TWO_STAGE_RETRAIN_ON_GENERALIZATION_SURFACE.

Ordering (hard):
  1 verify V1R1 READY + pins
  2 verify sealed split identity
  3 RESOLVE_V5_STAGE_A_V1R1_TWO_STAGE_CLASS_WEIGHTS (train only)
  4 seal V1R1_TWO_STAGE_CLASS_WEIGHTS.json
  5 freeze initialization policy (fresh from MODEL_WIDE_BEST)
  6 seal RESOLVED_TRAINING_CONFIG.json
  7 create authorization receipt → TRAIN_AUTHORIZED=true

Does not train. Does not mutate V1R1. Does not move BEST. Does not touch reserve.
Does not overwrite HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001.
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
REMEDIATION_DELTA_SHA = (
    "f560fb93302bd30980db8f5dd2ba8aaac1ecad1adf6a3a34e42e631bab70a006"
)
ARCHITECTURE_RECEIPT_SHA = (
    "631427cc4c1b09bac1e3a2c5e081c7e9fc0947babda26c03cb73895f47754697"
)
AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-two-stage-generalization-train-v1-20261001"
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
    / "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001"
)
SPEC_DIR = REPO / "specs" / "007-hyperlexical-model"
PUBLIC_DESIGN_RECEIPT = (
    SPEC_DIR
    / "classification-v5-stage-a-two-stage-decision-graph-v1-receipt-20260930.json"
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
    from hyperlexical.classification_v5_stage_a_gold_label_mapping import (
        admission_invariants,
    )
    from hyperlexical.classification_v5_stage_a_two_stage import (
        ARCHITECTURE_RECEIPT_SHA256,
        identity_list_sha256,
    )
    from hyperlexical.classification_v5_stage_a_two_stage_generalization import (
        AUTHORIZE_RULE,
        AUTHORIZED_DATASET_SHA,
        AUTHORIZED_READINESS_SHA,
        AUTHORIZED_SURFACE_RECEIPT_SHA,
        AUTHORIZED_SURFACE_RULE,
        AUTHORIZED_SURFACE_VERSION,
        EXPECTED_TRAIN_IDENTITY_LIST_SHA256,
        EXPECTED_TRAIN_ROWS,
        EXPECTED_TRAIN_SPLIT_SHA256,
        EXPECTED_VALIDATION_IDENTITY_LIST_SHA256,
        EXPECTED_VALIDATION_ROWS,
        EXPECTED_VALIDATION_SPLIT_SHA256,
        EXPERIMENT_ID,
        INITIALIZATION_POLICY,
        PARENT_STAGE_A_BEST_SHA,
        PARENT_TWO_STAGE_EXPERIMENT_ID,
        SPENT_RESERVE,
        SPENT_RESERVE_OVERLAP,
        SPENT_RESERVE_STATUS,
        TRAIN_ONCE_ACTION,
        TRAIN_RULE,
        generalization_authorization_contract,
        generalization_resolved_config,
        generalization_runner_authorization_checks,
        resolve_v1r1_two_stage_class_weights,
        verify_v1r1_split_pins,
    )

    if AUTHORIZED_DATASET_SHA != DATASET_SHA:
        fail("AUTHORIZED_DATASET_SHA pin mismatch")
    if ARCHITECTURE_RECEIPT_SHA256 != ARCHITECTURE_RECEIPT_SHA:
        fail("ARCHITECTURE_RECEIPT_SHA256 pin mismatch")
    if AUTHORIZE_RULE != (
        "AUTHORIZE_V5_STAGE_A_TWO_STAGE_RETRAIN_ON_GENERALIZATION_SURFACE"
    ):
        fail("AUTHORIZE_RULE pin mismatch")
    if EXPERIMENT_ID != (
        "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001"
    ):
        fail("EXPERIMENT_ID pin mismatch")
    if EXPERIMENT_ID == PARENT_TWO_STAGE_EXPERIMENT_ID:
        fail("must_not_overwrite_prior_two_stage_experiment")
    if INITIALIZATION_POLICY["stage_a_best_continuation"] is not False:
        fail("initialization_policy_conflict:stage_a_best_continuation")
    if INITIALIZATION_POLICY["base_encoder_sha256"] != BEST_SHA:
        fail("initialization_policy_conflict:base_encoder")

    if not PUBLIC_DESIGN_RECEIPT.is_file():
        fail(f"missing architecture receipt:{PUBLIC_DESIGN_RECEIPT}")
    sealed = json.loads(PUBLIC_DESIGN_RECEIPT.read_text(encoding="utf-8"))
    sealed_sha = sealed.get("design_receipt_sha256")
    if sealed_sha != ARCHITECTURE_RECEIPT_SHA:
        fail(
            "architecture_receipt_mismatch:"
            f"file={sealed_sha} pin={ARCHITECTURE_RECEIPT_SHA}"
        )
    recomputed = sha256_text(
        canonical_json(
            {k: v for k, v in sealed.items() if k != "design_receipt_sha256"}
        )
    )
    if recomputed != ARCHITECTURE_RECEIPT_SHA:
        fail("architecture_receipt_body_digest_mismatch")

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset digest mismatch")
    if sha256_file(SURFACE / "READINESS.json") != READINESS_SHA:
        fail("readiness digest mismatch")
    if sha256_file(SURFACE / "REMEDIATION_DELTA.json") != REMEDIATION_DELTA_SHA:
        fail("remediation_delta digest mismatch")
    if PUBLIC_SURFACE_RECEIPT.is_file():
        if sha256_file(PUBLIC_SURFACE_RECEIPT) != SURFACE_RECEIPT_SHA:
            # receipt_sha256 field may be content-hash; also accept body pin
            pub = json.loads(PUBLIC_SURFACE_RECEIPT.read_text(encoding="utf-8"))
            if pub.get("receipt_sha256") != SURFACE_RECEIPT_SHA:
                fail("surface_receipt digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not TRUNK.exists():
        fail("tokenizer trunk missing")

    readiness = json.loads((SURFACE / "READINESS.json").read_text(encoding="utf-8"))
    if readiness.get("state") != "READY" or not readiness.get("ready"):
        fail("surface readiness not READY")
    if not all(readiness.get("gate_pass", {}).values()):
        fail(f"readiness gate_pass incomplete:{readiness.get('gate_pass')}")
    if readiness.get("surface_rule") != AUTHORIZED_SURFACE_RULE:
        fail("surface_rule mismatch")

    manifest = json.loads((SURFACE / "MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.get("dataset_sha256") != DATASET_SHA:
        fail("manifest dataset mismatch")
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

    train_rows = [row for row in rows if row.get("split") == "train"]
    val_rows = [row for row in rows if row.get("split") == "validation"]
    train_split_sha = split_lines_sha256(DATASET, split="train")
    val_split_sha = split_lines_sha256(DATASET, split="validation")
    train_id_sha = identity_list_sha256(train_ids)
    val_id_sha = identity_list_sha256(val_ids)
    # Also verify live row identity lists match sealed manifest.
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

    revision = code_revision()

    # --- RESOLVE_V5_STAGE_A_V1R1_TWO_STAGE_CLASS_WEIGHTS ---
    weights = resolve_v1r1_two_stage_class_weights(
        train_rows,
        dataset_sha256=DATASET_SHA,
        train_split_sha256=train_split_sha,
        train_identity_list_sha256=train_id_sha,
        code_revision=revision,
    )
    if weights["dataset_sha256"] != DATASET_SHA:
        fail("CLASS_WEIGHT_RESOLUTION_INVALID:dataset")
    if weights["Gate1"]["coverage"]["n_train"] != EXPECTED_TRAIN_ROWS:
        fail("CLASS_WEIGHT_RESOLUTION_INVALID:gate1_total")
    expected_g2 = (
        weights["Gate1"]["coverage"]["n_possible"]
    )
    if weights["Gate2"]["coverage"]["n_eligible"] != expected_g2:
        fail("CLASS_WEIGHT_RESOLUTION_INVALID:gate2_total")
    if (
        weights["Gate1"]["possible_evidence_identity_list_sha256"]
        != weights["Gate2"]["eligible_identity_list_sha256"]
    ):
        fail("CLASS_WEIGHT_RESOLUTION_INVALID:identity_hash")

    tokenizer_identity = f"local_files_only:{TRUNK.name}"
    resolved = generalization_resolved_config(
        dataset_sha256=DATASET_SHA,
        class_weight_artifact=weights,
        code_revision=revision,
        tokenizer_identity=tokenizer_identity,
        train_split_sha256=train_split_sha,
        validation_split_sha256=val_split_sha,
        train_identity_list_sha256=train_id_sha,
        validation_identity_list_sha256=val_id_sha,
        readiness_sha256=READINESS_SHA,
        surface_receipt_sha256=SURFACE_RECEIPT_SHA,
    )
    auth = generalization_authorization_contract(
        dataset_sha256=DATASET_SHA,
        training_config_sha256=resolved["training_config_sha256"],
        class_weight_artifact_sha256=weights["CLASS_WEIGHT_ARTIFACT_SHA256"],
        code_revision=revision,
        readiness_sha256=READINESS_SHA,
        surface_receipt_sha256=SURFACE_RECEIPT_SHA,
    )
    auth["INPUT_IDENTITY"] = "PASS"
    auth["SURFACE_READINESS"] = "PASS"
    auth["LABEL_MAPPING"] = "PASS"
    auth["SPLIT_IDENTITY"] = "PASS"
    auth["authorized_surface_dir"] = str(SURFACE)
    auth["label_provenance_statistics"] = provenance["statistics"]
    auth["label_provenance_n_valid"] = provenance["n_valid"]
    auth["label_provenance_invalid"] = provenance["invalid_provenance_rows"]
    auth["gold_mapping_sha256"] = resolved["gold_mapping_sha256"]
    auth["label_provenance_contract_sha256"] = resolved[
        "label_provenance_contract_sha256"
    ]
    auth["gate1_class_weights_literal"] = resolved["gate1_class_weights_literal"]
    auth["gate2_class_weights_literal"] = resolved["gate2_class_weights_literal"]
    auth["split_pins"] = split_pin["expected"]
    auth["runner_checks"] = generalization_runner_authorization_checks(
        train_authorized=True,
        experiment_id=EXPERIMENT_ID,
        dataset_sha256=DATASET_SHA,
        architecture_receipt_sha256=ARCHITECTURE_RECEIPT_SHA,
        resolved_config_sha256=resolved["training_config_sha256"],
        authorized_config_sha256=resolved["training_config_sha256"],
        best_sha256=BEST_SHA,
        stage_a_best_sha256=STAGE_A_BEST_SHA,
        surface_readiness="PASS",
        label_mapping="PASS",
        label_provenance_invalid_rows=provenance["invalid_provenance_rows"],
        prior_run_count=0,
        reserve_consumed=False,
        class_weight_artifact_sha256=weights["CLASS_WEIGHT_ARTIFACT_SHA256"],
        authorized_class_weight_artifact_sha256=weights[
            "CLASS_WEIGHT_ARTIFACT_SHA256"
        ],
        readiness_sha256=READINESS_SHA,
        surface_receipt_sha256=SURFACE_RECEIPT_SHA,
        initialization_stage_a_best_continuation=False,
    )
    if not auth["runner_checks"]["pass"]:
        fail(f"runner_checks_failed:{auth['runner_checks']}")
    auth["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in auth.items() if k != "receipt_sha256"})
    )

    if AUTH_DEST.exists() and (AUTH_DEST / "AUTHORIZATION.json").exists():
        fail(f"authorization already sealed:{AUTH_DEST}")

    AUTH_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(AUTH_DEST, 0o700)

    write_private(AUTH_DEST / "V1R1_TWO_STAGE_CLASS_WEIGHTS.json", weights)
    write_private(AUTH_DEST / "TWO_STAGE_CLASS_WEIGHTS.json", weights)
    write_private(AUTH_DEST / "RESOLVED_TRAINING_CONFIG.json", resolved)
    write_private(AUTH_DEST / "AUTHORIZATION.json", auth)
    write_private(AUTH_DEST / "INITIALIZATION_POLICY.json", INITIALIZATION_POLICY)
    write_private(AUTH_DEST / "SPLIT_PIN.json", split_pin)
    write_private(
        AUTH_DEST / "LABEL_PROVENANCE_STATS.json",
        {
            "invalid_provenance_rows": provenance["invalid_provenance_rows"],
            "n_valid": provenance["n_valid"],
            "pass": provenance["pass"],
            "statistics": provenance["statistics"],
        },
    )
    body = "\n".join(canonical_json(record) for record in provenance["records"]) + "\n"
    write_private(AUTH_DEST / "LABEL_PROVENANCE.jsonl", body)

    train_contract = {
        **resolved["acceptance_gates"],
        "architecture_receipt_sha256": ARCHITECTURE_RECEIPT_SHA,
        "class_weight_artifact_sha256": weights["CLASS_WEIGHT_ARTIFACT_SHA256"],
        "contract_sha256": None,
        "experiment_id": EXPERIMENT_ID,
        "initialization_policy": INITIALIZATION_POLICY,
        "preregistered": True,
        "readiness_sha256": READINESS_SHA,
        "rule": TRAIN_RULE,
        "scope": "model_acceptance_after_authorized_two_stage_generalization_train",
        "spent_reserve": SPENT_RESERVE,
        "spent_reserve_overlap": SPENT_RESERVE_OVERLAP,
        "spent_reserve_status": SPENT_RESERVE_STATUS,
        "surface_dataset_sha256": DATASET_SHA,
        "surface_ready": True,
        "surface_receipt_sha256": SURFACE_RECEIPT_SHA,
        "surface_rule": AUTHORIZED_SURFACE_RULE,
        "surface_version": AUTHORIZED_SURFACE_VERSION,
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
        AUTH_DEST / "STAGE_A_TWO_STAGE_GENERALIZATION_TRAIN_CONTRACT.json",
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
                "stage_a_two_stage_generalization_auth_hashes.v1"
            ),
        },
    )

    summary = {
        "ARCHITECTURE_RECEIPT_SHA256": ARCHITECTURE_RECEIPT_SHA,
        "AUTHORIZATION_RECEIPT_SHA256": auth["receipt_sha256"],
        "BEST_MUTATED": False,
        "CLASS_WEIGHT_ARTIFACT_SHA256": weights["CLASS_WEIGHT_ARTIFACT_SHA256"],
        "CODE_REVISION": revision,
        "CURRENT_BEST": BEST_SHA,
        "DATASET_SHA256": DATASET_SHA,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "INITIALIZATION_POLICY": INITIALIZATION_POLICY["policy"],
        "INPUT_IDENTITY": "PASS",
        "LABEL_MAPPING": "PASS",
        "MODEL_WIDE_BEST": BEST_SHA,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": TRAIN_ONCE_ACTION,
        "PARENT_STAGE_A_BEST": STAGE_A_BEST_SHA,
        "PARENT_STAGE_A_BEST_MUTATED": False,
        "PARENT_TWO_STAGE_EXPERIMENT_ID": PARENT_TWO_STAGE_EXPERIMENT_ID,
        "PRIVATE_AUTH_DIR": str(AUTH_DEST),
        "READINESS_SHA256": READINESS_SHA,
        "RESERVE_CONSUMED": False,
        "SCIENTIFIC_RESULT": "NOT_COMPUTABLE",
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_OVERLAP": SPENT_RESERVE_OVERLAP,
        "STAGE_B_MUTATED": False,
        "SURFACE_READINESS": "PASS",
        "SURFACE_RECEIPT_SHA256": SURFACE_RECEIPT_SHA,
        "TRAINING_CONFIG_SHA256": resolved["training_config_sha256"],
        "TRAINING_RUN_LIMIT": 1,
        "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
        "TRAIN_AUTHORIZED": True,
        "TRAIN_IDENTITY_LIST_SHA256": EXPECTED_TRAIN_IDENTITY_LIST_SHA256,
        "TRAIN_ROWS": EXPECTED_TRAIN_ROWS,
        "TRAIN_SPLIT_SHA256": EXPECTED_TRAIN_SPLIT_SHA256,
        "VALIDATION_IDENTITY_LIST_SHA256": EXPECTED_VALIDATION_IDENTITY_LIST_SHA256,
        "VALIDATION_ROWS": EXPECTED_VALIDATION_ROWS,
        "VALIDATION_SPLIT_SHA256": EXPECTED_VALIDATION_SPLIT_SHA256,
        "authorize_rule": AUTHORIZE_RULE,
        "gate1_class_weights": resolved["gate1_class_weights_literal"],
        "gate1_counts": {
            "NO_EVIDENCE": weights["Gate1"]["NO_EVIDENCE"],
            "POSSIBLE_EVIDENCE": weights["Gate1"]["POSSIBLE_EVIDENCE"],
        },
        "gate2_class_weights": resolved["gate2_class_weights_literal"],
        "gate2_counts": {
            "CONFIRMED_PRESENT": weights["Gate2"]["CONFIRMED_PRESENT"],
            "UNCERTAIN": weights["Gate2"]["UNCERTAIN"],
        },
        "label_provenance_invalid": provenance["invalid_provenance_rows"],
        "rule": TRAIN_RULE,
        "surface_rule": AUTHORIZED_SURFACE_RULE,
        "surface_version": AUTHORIZED_SURFACE_VERSION,
        "train": False,
    }
    write_private(AUTH_DEST / "SUMMARY.json", summary)

    public_receipt = {
        "ARCHITECTURE_RECEIPT_SHA256": ARCHITECTURE_RECEIPT_SHA,
        "AUTHORIZATION_RECEIPT_SHA256": auth["receipt_sha256"],
        "BEST": "UNCHANGED",
        "BEST_SHA256": BEST_SHA,
        "CLASS_WEIGHT_ARTIFACT_SHA256": weights["CLASS_WEIGHT_ARTIFACT_SHA256"],
        "DATASET_SHA256": DATASET_SHA,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "INITIALIZATION_POLICY": INITIALIZATION_POLICY,
        "MODEL_WIDE_BEST": BEST_SHA,
        "NEXT_ACTION": TRAIN_ONCE_ACTION,
        "PARENT_STAGE_A_BEST": STAGE_A_BEST_SHA,
        "READINESS_SHA256": READINESS_SHA,
        "RESERVE": "SPENT_UNUSED",
        "SCIENTIFIC_RESULT": "NOT_COMPUTABLE",
        "SURFACE_RECEIPT_SHA256": SURFACE_RECEIPT_SHA,
        "TRAINING_CONFIG_SHA256": resolved["training_config_sha256"],
        "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
        "TRAIN_AUTHORIZED": True,
        "TRAIN_IDENTITY_LIST_SHA256": EXPECTED_TRAIN_IDENTITY_LIST_SHA256,
        "TRAIN_ROWS": EXPECTED_TRAIN_ROWS,
        "TRAIN_SPLIT_SHA256": EXPECTED_TRAIN_SPLIT_SHA256,
        "VALIDATION_IDENTITY_LIST_SHA256": EXPECTED_VALIDATION_IDENTITY_LIST_SHA256,
        "VALIDATION_ROWS": EXPECTED_VALIDATION_ROWS,
        "VALIDATION_SPLIT_SHA256": EXPECTED_VALIDATION_SPLIT_SHA256,
        "authorize_rule": AUTHORIZE_RULE,
        "gate1_class_weights": resolved["gate1_class_weights_literal"],
        "gate1_counts": summary["gate1_counts"],
        "gate2_class_weights": resolved["gate2_class_weights_literal"],
        "gate2_counts": summary["gate2_counts"],
        "rule": TRAIN_RULE,
        "surface_rule": AUTHORIZED_SURFACE_RULE,
        "surface_version": AUTHORIZED_SURFACE_VERSION,
        "train": False,
    }
    public_receipt["receipt_sha256"] = sha256_text(
        canonical_json(
            {k: v for k, v in public_receipt.items() if k != "receipt_sha256"}
        )
    )

    write_repo(REPO_ARTIFACTS / "summary.json", summary)
    write_repo(REPO_ARTIFACTS / "authorization_receipt.json", public_receipt)
    write_repo(REPO_ARTIFACTS / "V1R1_TWO_STAGE_CLASS_WEIGHTS.json", weights)
    write_repo(REPO_ARTIFACTS / "RESOLVED_TRAINING_CONFIG.json", resolved)
    write_repo(REPO_ARTIFACTS / "INITIALIZATION_POLICY.json", INITIALIZATION_POLICY)
    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-two-stage-generalization-authorize-receipt-20261001.json",
        public_receipt,
    )

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
