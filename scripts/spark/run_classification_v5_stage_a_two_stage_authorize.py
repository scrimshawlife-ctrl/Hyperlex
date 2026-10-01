"""AUTHORIZE_V5_STAGE_A_TWO_STAGE_TRAIN_V1 — freeze recipe; do not train.

Ordering (hard):
  1 verify V1R9 identity + architecture receipt pin
  2 resolve class counts / weights on train only
  3 seal TWO_STAGE_CLASS_WEIGHTS.json
  4 build resolved training config with literal weights
  5 compute TRAINING_CONFIG_SHA256
  6 create authorization receipt
  7 TRAIN_AUTHORIZED=true / AUTHORIZED_NOT_STARTED

Does not train. Does not modify V1R9 body. Does not move BEST or reserve.
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
    "classification-v5-stage-a-negative-evidence-surface-v1r9-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a"
ARCHITECTURE_RECEIPT_SHA = (
    "631427cc4c1b09bac1e3a2c5e081c7e9fc0947babda26c03cb73895f47754697"
)
AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-two-stage-train-v1-20260930"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001"
)
SPEC_DIR = REPO / "specs" / "007-hyperlexical-model"
PUBLIC_DESIGN_RECEIPT = (
    SPEC_DIR
    / "classification-v5-stage-a-two-stage-decision-graph-v1-receipt-20260930.json"
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


def train_split_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("split") == "train":
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
        AUTHORIZE_RULE,
        AUTHORIZED_DATASET_SHA,
        AUTHORIZED_SURFACE_RULE,
        EXPERIMENT_ID,
        TRAIN_ONCE_ACTION,
        TRAIN_RULE,
        authorization_contract,
        resolve_two_stage_class_weights,
        runner_authorization_checks,
        two_stage_resolved_config,
    )

    if AUTHORIZED_DATASET_SHA != DATASET_SHA:
        fail("AUTHORIZED_DATASET_SHA pin mismatch")
    if ARCHITECTURE_RECEIPT_SHA256 != ARCHITECTURE_RECEIPT_SHA:
        fail("ARCHITECTURE_RECEIPT_SHA256 pin mismatch")
    if AUTHORIZE_RULE != "AUTHORIZE_V5_STAGE_A_TWO_STAGE_TRAIN_V1":
        fail("AUTHORIZE_RULE pin mismatch")
    if EXPERIMENT_ID != "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001":
        fail("EXPERIMENT_ID pin mismatch")

    if not PUBLIC_DESIGN_RECEIPT.is_file():
        fail(f"missing architecture receipt:{PUBLIC_DESIGN_RECEIPT}")
    sealed = json.loads(PUBLIC_DESIGN_RECEIPT.read_text(encoding="utf-8"))
    sealed_sha = sealed.get("design_receipt_sha256")
    if sealed_sha != ARCHITECTURE_RECEIPT_SHA:
        fail(
            "architecture_receipt_mismatch:"
            f"file={sealed_sha} pin={ARCHITECTURE_RECEIPT_SHA}"
        )
    # Recompute digest over sealed body (excluding hash field) for fail-closed bind.
    recomputed = sha256_text(
        canonical_json(
            {k: v for k, v in sealed.items() if k != "design_receipt_sha256"}
        )
    )
    if recomputed != ARCHITECTURE_RECEIPT_SHA:
        fail("architecture_receipt_body_digest_mismatch")

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not TRUNK.exists():
        fail("tokenizer trunk missing")

    readiness = json.loads((SURFACE / "READINESS.json").read_text(encoding="utf-8"))
    if readiness.get("state") != "READY":
        fail("surface readiness not READY")
    if readiness.get("dataset_sha256") != DATASET_SHA:
        fail("readiness dataset mismatch")
    details = readiness.get("readiness_details") or {}
    gate_pass = {
        key: bool(value.get("pass"))
        for key, value in details.items()
        if isinstance(value, dict) and "pass" in value
    }
    if not gate_pass or not all(gate_pass.values()):
        fail(f"readiness_details incomplete:{gate_pass}")

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
    if len(train_rows) != 4437:
        fail(f"unexpected_train_count:{len(train_rows)}")
    split_sha = train_split_sha256(DATASET)
    revision = code_revision()

    # --- RESOLVE_V5_TWO_STAGE_CLASS_WEIGHTS (must precede TRAIN_AUTHORIZED) ---
    weights = resolve_two_stage_class_weights(
        train_rows,
        dataset_sha256=DATASET_SHA,
        train_split_sha256=split_sha,
        code_revision=revision,
    )
    if weights["dataset_sha256"] != DATASET_SHA:
        fail("CLASS_WEIGHT_RESOLUTION_INVALID:dataset")

    tokenizer_identity = f"local_files_only:{TRUNK.name}"
    resolved = two_stage_resolved_config(
        dataset_sha256=DATASET_SHA,
        class_weight_artifact=weights,
        code_revision=revision,
        tokenizer_identity=tokenizer_identity,
        architecture_receipt_sha256=ARCHITECTURE_RECEIPT_SHA,
    )
    auth = authorization_contract(
        dataset_sha256=DATASET_SHA,
        training_config_sha256=resolved["training_config_sha256"],
        class_weight_artifact_sha256=weights["CLASS_WEIGHT_ARTIFACT_SHA256"],
        code_revision=revision,
        architecture_receipt_sha256=ARCHITECTURE_RECEIPT_SHA,
    )
    auth["INPUT_IDENTITY"] = "PASS"
    auth["SURFACE_READINESS"] = "PASS"
    auth["LABEL_MAPPING"] = "PASS"
    auth["gate_eval_sha256"] = readiness.get("gate_eval_sha256")
    auth["readiness_receipt_sha256"] = readiness.get("receipt_sha256")
    auth["label_provenance_statistics"] = provenance["statistics"]
    auth["label_provenance_n_valid"] = provenance["n_valid"]
    auth["label_provenance_invalid"] = provenance["invalid_provenance_rows"]
    auth["authorized_surface_dir"] = str(SURFACE)
    auth["gold_mapping_sha256"] = resolved["gold_mapping_sha256"]
    auth["label_provenance_contract_sha256"] = resolved[
        "label_provenance_contract_sha256"
    ]
    auth["gate1_class_weights_literal"] = resolved["gate1_class_weights_literal"]
    auth["gate2_class_weights_literal"] = resolved["gate2_class_weights_literal"]
    auth["runner_checks"] = runner_authorization_checks(
        train_authorized=True,
        experiment_id=EXPERIMENT_ID,
        dataset_sha256=DATASET_SHA,
        architecture_receipt_sha256=ARCHITECTURE_RECEIPT_SHA,
        resolved_config_sha256=resolved["training_config_sha256"],
        authorized_config_sha256=resolved["training_config_sha256"],
        best_sha256=BEST_SHA,
        surface_readiness="PASS",
        label_mapping="PASS",
        label_provenance_invalid_rows=provenance["invalid_provenance_rows"],
        prior_run_count=0,
        reserve_consumed=False,
        class_weight_artifact_sha256=weights["CLASS_WEIGHT_ARTIFACT_SHA256"],
        authorized_class_weight_artifact_sha256=weights[
            "CLASS_WEIGHT_ARTIFACT_SHA256"
        ],
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

    write_private(AUTH_DEST / "TWO_STAGE_CLASS_WEIGHTS.json", weights)
    write_private(AUTH_DEST / "RESOLVED_TRAINING_CONFIG.json", resolved)
    write_private(AUTH_DEST / "AUTHORIZATION.json", auth)
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
        "preregistered": True,
        "rule": TRAIN_RULE,
        "scope": "model_acceptance_after_authorized_two_stage_train",
        "surface_dataset_sha256": DATASET_SHA,
        "surface_ready": True,
        "surface_rule": AUTHORIZED_SURFACE_RULE,
        "train_authorized": True,
        "training_config_sha256": resolved["training_config_sha256"],
        "training_run_limit": 1,
        "training_status": "AUTHORIZED_NOT_STARTED",
    }
    train_contract["contract_sha256"] = sha256_text(
        canonical_json({k: v for k, v in train_contract.items() if k != "contract_sha256"})
    )
    write_private(AUTH_DEST / "STAGE_A_TWO_STAGE_TRAIN_CONTRACT.json", train_contract)

    # Surface settlement next-action pointer (metadata); dataset body untouched.
    settlement_path = SURFACE / "SETTLEMENT.json"
    settlement = json.loads(settlement_path.read_text(encoding="utf-8"))
    settlement_out = dict(settlement)
    settlement_out["next_action"] = TRAIN_ONCE_ACTION
    settlement_out["two_stage_train_authorized"] = True
    settlement_out["two_stage_authorization_receipt_sha256"] = auth["receipt_sha256"]
    settlement_out["two_stage_training_config_sha256"] = resolved[
        "training_config_sha256"
    ]
    settlement_out["settlement_sha256"] = sha256_text(
        canonical_json(
            {k: v for k, v in settlement_out.items() if k != "settlement_sha256"}
        )
    )
    write_private(settlement_path, settlement_out)

    hashes = {}
    for path in sorted(AUTH_DEST.iterdir()):
        if path.is_file():
            hashes[path.name] = sha256_file(path)
    write_private(
        AUTH_DEST / "ARTIFACT_HASHES.json",
        {
            "files": hashes,
            "schema": "hyperlex.classification.v5.stage_a_two_stage_auth_hashes.v1",
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
        "INPUT_IDENTITY": "PASS",
        "LABEL_MAPPING": "PASS",
        "NEXT_ACTION": TRAIN_ONCE_ACTION,
        "PRIVATE_AUTH_DIR": str(AUTH_DEST),
        "RESERVE_CONSUMED": False,
        "SCIENTIFIC_RESULT": "NOT_COMPUTABLE",
        "SURFACE_READINESS": "PASS",
        "TRAINING_CONFIG_SHA256": resolved["training_config_sha256"],
        "TRAINING_RUN_LIMIT": 1,
        "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
        "TRAIN_AUTHORIZED": True,
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
        "train": False,
        "train_split_sha256": split_sha,
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
        "NEXT_ACTION": TRAIN_ONCE_ACTION,
        "RESERVE": "unused",
        "SCIENTIFIC_RESULT": "NOT_COMPUTABLE",
        "TRAINING_CONFIG_SHA256": resolved["training_config_sha256"],
        "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
        "TRAIN_AUTHORIZED": True,
        "authorize_rule": AUTHORIZE_RULE,
        "gate1_class_weights": resolved["gate1_class_weights_literal"],
        "gate2_class_weights": resolved["gate2_class_weights_literal"],
        "rule": TRAIN_RULE,
        "surface_rule": AUTHORIZED_SURFACE_RULE,
        "train": False,
    }
    write_repo(REPO_ARTIFACTS / "summary.json", summary)
    write_repo(REPO_ARTIFACTS / "authorization_receipt.json", public_receipt)
    write_repo(REPO_ARTIFACTS / "TWO_STAGE_CLASS_WEIGHTS.json", weights)
    write_repo(REPO_ARTIFACTS / "RESOLVED_TRAINING_CONFIG.json", resolved)
    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-two-stage-train-authorize-receipt-20260930.json",
        public_receipt,
    )

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
