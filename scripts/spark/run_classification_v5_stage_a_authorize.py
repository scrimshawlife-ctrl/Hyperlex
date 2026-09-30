"""AUTHORIZE_V5_STAGE_A_TRAIN_V1 — freeze recipe + authorize one run.

Does not train. Does not modify the READY dataset body. Does not move BEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-negative-evidence-surface-v1r7-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "a81ca68ad3310981c60d2500a83a0989adeb967cbee6ad6dff003ed2c705efa9"
READINESS_SHA = "f07e4c04708bdb0e0e58f91e11d393f852356822f0d9531336667af25b713a40"
GATE_EVAL_SHA = "0a4ad7871351f592371aa93e44207b19039949c4acc598daf69e8b225217af11"
AUTH_DEST = Path("/home/morpheus/hlx-private/classification-v5-stage-a-train-20260930")
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
EXPECTED_CODE_HINT = "60bfb07"  # stop commit or later on authorize branch

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
        AUTHORIZED_DATASET_SHA,
        AUTHORIZED_SURFACE_RULE,
        EXPERIMENT_ID,
        LABEL_PROVENANCE_RULE,
        STAGE_A_RULE,
        attach_and_validate_label_provenance,
        build_resolved_training_config,
        canonical_json,
        compute_class_weights,
        sha256_text,
        stage_a_authorization_contract,
    )

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset digest mismatch")
    readiness = json.loads((SURFACE / "READINESS.json").read_text(encoding="utf-8"))
    if readiness.get("receipt_sha256") != READINESS_SHA:
        fail("readiness receipt mismatch")
    if readiness.get("state") != "READY":
        fail("surface not READY")
    gate_eval = json.loads((SURFACE / "GATE_EVAL.json").read_text(encoding="utf-8"))
    if gate_eval.get("gate_eval_sha256") != GATE_EVAL_SHA:
        fail("gate_eval digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not TRUNK.exists():
        fail("tokenizer trunk missing")

    details = readiness.get("readiness_details") or {}
    gate_pass = {
        key: bool(value.get("pass"))
        for key, value in details.items()
        if isinstance(value, dict) and "pass" in value
    }
    if not gate_pass or not all(gate_pass.values()):
        fail(f"readiness gates incomplete:{gate_pass}")

    rows = load_jsonl(DATASET)
    train_rows = [row for row in rows if row.get("split") == "train"]
    if len(train_rows) < 100:
        fail("train split too small")

    class_weights = compute_class_weights(train_rows)
    provenance = attach_and_validate_label_provenance(rows)
    if not provenance["pass"]:
        fail(
            "LABEL_PROVENANCE_INVALID:"
            + json.dumps(provenance["invalid_samples"][:5], sort_keys=True)
        )

    revision = code_revision()
    tokenizer_identity = f"local_files_only:{TRUNK.name}"
    resolved = build_resolved_training_config(
        dataset_sha256=DATASET_SHA,
        class_weight_report=class_weights,
        code_revision=revision,
        tokenizer_identity=tokenizer_identity,
        surface_rule=AUTHORIZED_SURFACE_RULE,
    )
    auth = stage_a_authorization_contract(
        dataset_sha256=DATASET_SHA,
        training_config_sha256=resolved["training_config_sha256"],
        code_revision=revision,
    )
    auth["INPUT_IDENTITY"] = "PASS"
    auth["SURFACE_READINESS"] = "PASS"
    auth["gate_eval_sha256"] = GATE_EVAL_SHA
    auth["readiness_receipt_sha256"] = READINESS_SHA
    auth["label_provenance_statistics"] = provenance["statistics"]
    auth["label_provenance_n_valid"] = provenance["n_valid"]
    auth["label_provenance_invalid"] = provenance["invalid_provenance_rows"]
    auth["authorized_surface_dir"] = str(SURFACE)
    auth["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in auth.items() if k != "receipt_sha256"})
    )

    if AUTH_DEST.exists() and (AUTH_DEST / "AUTHORIZATION.json").exists():
        fail(f"authorization already sealed:{AUTH_DEST}")

    AUTH_DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(AUTH_DEST, 0o700)

    write_private(AUTH_DEST / "RESOLVED_TRAINING_CONFIG.json", resolved)
    write_private(AUTH_DEST / "AUTHORIZATION.json", auth)
    write_private(AUTH_DEST / "CLASS_WEIGHTS.json", class_weights)
    write_private(
        AUTH_DEST / "LABEL_PROVENANCE_STATS.json",
        {
            "invalid_provenance_rows": provenance["invalid_provenance_rows"],
            "n_valid": provenance["n_valid"],
            "pass": provenance["pass"],
            "rule": LABEL_PROVENANCE_RULE,
            "statistics": provenance["statistics"],
        },
    )
    # Sidecar only — does not rewrite EVIDENCE_SURFACE.jsonl / dataset SHA.
    body = "\n".join(canonical_json(record) for record in provenance["records"]) + "\n"
    write_private(AUTH_DEST / "LABEL_PROVENANCE.jsonl", body)

    train_contract = {
        **auth["acceptance_gates"],
        "contract_sha256": None,
        "experiment_id": EXPERIMENT_ID,
        "preregistered": True,
        "rule": STAGE_A_RULE,
        "scope": "model_acceptance_after_authorized_train",
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
    write_private(AUTH_DEST / "STAGE_A_TRAIN_CONTRACT.json", train_contract)
    # Mirror authorized contract onto the READY surface dir (metadata only).
    write_private(SURFACE / "STAGE_A_TRAIN_CONTRACT.json", train_contract)

    hashes = {}
    for path in sorted(AUTH_DEST.iterdir()):
        if path.is_file():
            hashes[path.name] = sha256_file(path)
    write_private(
        AUTH_DEST / "ARTIFACT_HASHES.json",
        {
            "files": hashes,
            "schema": "hyperlex.classification.v5.stage_a_auth_artifact_hashes.v1",
        },
    )

    summary = {
        "AUTHORIZATION_RECEIPT_SHA256": auth["receipt_sha256"],
        "CURRENT_BEST": BEST_SHA,
        "DATASET_SHA256": DATASET_SHA,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "INPUT_IDENTITY": "PASS",
        "NEXT_ACTION": "TRAIN_V5_STAGE_A_ONCE",
        "SCIENTIFIC_RESULT": "NOT_COMPUTABLE",
        "SURFACE_READINESS": "PASS",
        "TRAINING_CONFIG_SHA256": resolved["training_config_sha256"],
        "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
        "TRAIN_AUTHORIZED": True,
        "authorized_dataset_sha256": AUTHORIZED_DATASET_SHA,
        "code_revision": revision,
        "label_provenance_invalid": provenance["invalid_provenance_rows"],
        "label_provenance_n_valid": provenance["n_valid"],
        "private_auth_dir": str(AUTH_DEST),
        "rule": STAGE_A_RULE,
        "train": False,
    }
    write_private(AUTH_DEST / "SUMMARY.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
