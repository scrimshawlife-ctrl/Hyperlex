"""AUTHORIZE_V5_STAGE_A_NEXT_RUN_ON_REMEDIATED_SURFACE — V1R9 Stage-A-004.

Seals GATE_EVAL / READINESS digests on the READY V1R9 surface, freezes the
Stage-A train recipe, and authorizes exactly one run. Does not train. Does
not modify the READY dataset body. Does not move BEST or consume reserve.
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
    "classification-v5-stage-a-negative-evidence-surface-v1r9-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a"
PARENT_SURFACE_SHA = (
    "c0fdd82d1734585a7d852318ac5b390cc5e2c50908c0ef9f9eba4b3f7ebedc8b"
)
PARENT_DIAGNOSIS = "MIXED_UNCERTAIN_SURFACE_FAILURE"
AUTH_DEST = Path(
    "/home/morpheus/hlx-private/classification-v5-stage-a-train-v1r9-20260930"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
REPO_ARTIFACTS = (
    REPO / "artifacts" / "experiments" / "HLX-CLASSIFICATION-V5-STAGE-A-004"
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


def seal_gate_envelopes(
    *,
    evaluated: dict,
    uncertain_readiness: dict,
    settlement: dict,
    n_rows: int,
    surface_rule: str,
    gate_rule: str,
    canonical_json,
    sha256_text,
) -> tuple[dict, dict]:
    """Seal GATE_EVAL + READINESS digests without mutating the dataset body."""
    details = evaluated.get("details") or evaluated.get("readiness_details") or {}
    gate_pass = evaluated.get("gate_pass") or {}
    if evaluated.get("state") != "READY":
        fail("surface not READY before seal")
    if not gate_pass or not all(bool(v) for v in gate_pass.values()):
        fail(f"readiness gates incomplete:{gate_pass}")
    if uncertain_readiness.get("state") != "READY":
        fail("UNCERTAIN readiness not READY")
    uncertain_gates = uncertain_readiness.get("gates") or {}
    for name in uncertain_readiness.get("mandatory") or []:
        block = uncertain_gates.get(name) or {}
        if not block.get("pass"):
            fail(f"UNCERTAIN gate fail:{name}")

    missing = evaluated.get("missing_evidence") or {}
    model_acceptance = evaluated.get("model_acceptance_gates_separate") or {
        "EVIDENCE_PRESENT_recall_min": 0.7,
        "NO_EVIDENCE_recall_min": 0.9,
        "false_evidence_entry_rate_on_none_max": 0.05,
        "note": "model gates; not dataset-readiness gates",
    }

    gate_eval = {
        "BEST": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "dataset_sha256": DATASET_SHA,
        "gate_pass": gate_pass,
        "gate_rule": gate_rule,
        "gates": evaluated.get("gates") or {},
        "missing_evidence": missing,
        "model_acceptance_gates_separate": model_acceptance,
        "n": n_rows,
        "parent_diagnosis": PARENT_DIAGNOSIS,
        "parent_surface_dataset_sha256": PARENT_SURFACE_SHA,
        "remediate_rule": "REMEDIATE_V5_UNCERTAIN_SURFACE",
        "schema": "hyperlex.classification.v5.surface_gate_eval.v1",
        "state": "READY",
        "surface_rule": surface_rule,
        "train": False,
        "uncertain_gate_pass": {
            name: bool((uncertain_gates.get(name) or {}).get("pass"))
            for name in (uncertain_readiness.get("mandatory") or [])
        },
        "uncertain_readiness_state": uncertain_readiness.get("state"),
    }
    gate_eval["gate_eval_sha256"] = sha256_text(
        canonical_json({k: v for k, v in gate_eval.items() if k != "gate_eval_sha256"})
    )

    readiness = {
        "BEST": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "dataset_sha256": DATASET_SHA,
        "design_rule": "DESIGN_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE",
        "gate_eval_sha256": gate_eval["gate_eval_sha256"],
        "gate_pass": gate_pass,
        "gate_rule": gate_rule,
        "gates": evaluated.get("gates") or {},
        "missing_evidence": missing,
        "model_acceptance_gates_separate": model_acceptance,
        "n": n_rows,
        "n_train": settlement.get("n_train"),
        "n_validation": settlement.get("n_validation"),
        "parent_diagnosis": PARENT_DIAGNOSIS,
        "parent_surface_dataset_sha256": PARENT_SURFACE_SHA,
        "readiness": {
            "blockers": [],
            "missing_evidence": missing,
            "state": "READY",
            "surface_rule": surface_rule,
        },
        "readiness_details": details,
        "remediate_rule": "REMEDIATE_V5_UNCERTAIN_SURFACE",
        "schema": "hyperlex.classification.v5.evidence_surface_readiness.v1r9",
        "selected_checkpoint_sha256": settlement.get("selected_checkpoint_sha256"),
        "settlement_sha256": settlement.get("settlement_sha256"),
        "state": "READY",
        "surface_rule": surface_rule,
        "train": False,
        "uncertain_gate_pass": gate_eval["uncertain_gate_pass"],
        "uncertain_readiness_state": "READY",
    }
    readiness["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in readiness.items() if k != "receipt_sha256"})
    )
    return gate_eval, readiness


def main() -> int:
    from hyperlexical.classification_v5_stage_a import (
        AUTHORIZE_RULE,
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
    from hyperlexical.classification_v5_stage_a_uncertain_surface_remediate import (
        SURFACE_RULE_V1R9,
    )
    from hyperlexical.classification_v5_surface_readiness_gates import GATE_RULE

    if AUTHORIZED_DATASET_SHA != DATASET_SHA:
        fail("AUTHORIZED_DATASET_SHA pin mismatch")
    if AUTHORIZED_SURFACE_RULE != SURFACE_RULE_V1R9:
        fail("AUTHORIZED_SURFACE_RULE pin mismatch")
    if AUTHORIZE_RULE != "AUTHORIZE_V5_STAGE_A_NEXT_RUN_ON_REMEDIATED_SURFACE":
        fail("AUTHORIZE_RULE pin mismatch")
    if EXPERIMENT_ID != "HLX-CLASSIFICATION-V5-STAGE-A-004":
        fail("EXPERIMENT_ID pin mismatch")

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST weights changed")
    if not TRUNK.exists():
        fail("tokenizer trunk missing")

    evaluated = json.loads((SURFACE / "READINESS.json").read_text(encoding="utf-8"))
    uncertain_readiness = json.loads(
        (SURFACE / "UNCERTAIN_READINESS.json").read_text(encoding="utf-8")
    )
    settlement = json.loads((SURFACE / "SETTLEMENT.json").read_text(encoding="utf-8"))
    if settlement.get("final_state") != "READY":
        fail("settlement not READY")
    if settlement.get("dataset_sha256") != DATASET_SHA:
        fail("settlement dataset digest mismatch")
    if settlement.get("next_action") != AUTHORIZE_RULE:
        fail(f"unexpected next_action:{settlement.get('next_action')}")

    rows = load_jsonl(DATASET)
    gate_eval, readiness = seal_gate_envelopes(
        evaluated=evaluated,
        uncertain_readiness=uncertain_readiness,
        settlement=settlement,
        n_rows=len(rows),
        surface_rule=SURFACE_RULE_V1R9,
        gate_rule=GATE_RULE,
        canonical_json=canonical_json,
        sha256_text=sha256_text,
    )
    # Seal digests onto the READY surface (metadata only; dataset body untouched).
    if (SURFACE / "GATE_EVAL.json").exists():
        prior_gate = json.loads((SURFACE / "GATE_EVAL.json").read_text(encoding="utf-8"))
        if prior_gate.get("gate_eval_sha256") and prior_gate.get(
            "gate_eval_sha256"
        ) != gate_eval["gate_eval_sha256"]:
            # Re-seal only when prior was unsealed / thin envelope.
            if "gate_eval_sha256" in prior_gate and prior_gate.get("dataset_sha256"):
                fail("GATE_EVAL already sealed with different digest")
    write_private(SURFACE / "GATE_EVAL.json", gate_eval)
    write_private(SURFACE / "READINESS.json", readiness)

    gate_pass = {
        key: bool(value.get("pass"))
        for key, value in (readiness.get("readiness_details") or {}).items()
        if isinstance(value, dict) and "pass" in value
    }
    if not gate_pass or not all(gate_pass.values()):
        fail(f"readiness_details incomplete:{gate_pass}")

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
    auth["gate_eval_sha256"] = gate_eval["gate_eval_sha256"]
    auth["readiness_receipt_sha256"] = readiness["receipt_sha256"]
    auth["label_provenance_statistics"] = provenance["statistics"]
    auth["label_provenance_n_valid"] = provenance["n_valid"]
    auth["label_provenance_invalid"] = provenance["invalid_provenance_rows"]
    auth["authorized_surface_dir"] = str(SURFACE)
    auth["parent_diagnosis"] = PARENT_DIAGNOSIS
    auth["uncertain_readiness_state"] = "READY"
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
    write_private(SURFACE / "STAGE_A_TRAIN_CONTRACT.json", train_contract)

    # Update settlement next_action to TRAIN (authorize complete; train not started).
    settlement_out = dict(settlement)
    settlement_out["next_action"] = "TRAIN_V5_STAGE_A_ONCE"
    settlement_out["train_authorized"] = True
    settlement_out["authorization_receipt_sha256"] = auth["receipt_sha256"]
    settlement_out["gate_eval_sha256"] = gate_eval["gate_eval_sha256"]
    settlement_out["readiness_receipt_sha256"] = readiness["receipt_sha256"]
    settlement_out["settlement_sha256"] = sha256_text(
        canonical_json(
            {k: v for k, v in settlement_out.items() if k != "settlement_sha256"}
        )
    )
    write_private(SURFACE / "SETTLEMENT.json", settlement_out)

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
        "BEST_MUTATED": False,
        "CODE_REVISION": revision,
        "CURRENT_BEST": BEST_SHA,
        "DATASET_SHA256": DATASET_SHA,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "GATE_EVAL_SHA256": gate_eval["gate_eval_sha256"],
        "INPUT_IDENTITY": "PASS",
        "NEXT_ACTION": "TRAIN_V5_STAGE_A_ONCE",
        "PRIVATE_AUTH_DIR": str(AUTH_DEST),
        "READINESS_RECEIPT_SHA256": readiness["receipt_sha256"],
        "RESERVE_CONSUMED": False,
        "SCIENTIFIC_RESULT": "NOT_COMPUTABLE",
        "SURFACE_READINESS": "PASS",
        "TRAINING_CONFIG_SHA256": resolved["training_config_sha256"],
        "TRAINING_RUN_LIMIT": 1,
        "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
        "TRAIN_AUTHORIZED": True,
        "authorize_rule": AUTHORIZE_RULE,
        "authorized_dataset_sha256": AUTHORIZED_DATASET_SHA,
        "class_weights": class_weights.get("class_weights")
        or class_weights.get("weights")
        or class_weights,
        "label_provenance_invalid": provenance["invalid_provenance_rows"],
        "label_provenance_n_valid": provenance["n_valid"],
        "parent_diagnosis": PARENT_DIAGNOSIS,
        "parent_surface_dataset_sha256": PARENT_SURFACE_SHA,
        "rule": STAGE_A_RULE,
        "surface_rule": AUTHORIZED_SURFACE_RULE,
        "train": False,
    }
    write_private(AUTH_DEST / "SUMMARY.json", summary)

    # Public experiment mirror (no private row bodies).
    write_repo(REPO_ARTIFACTS / "summary.json", summary)
    write_repo(
        REPO_ARTIFACTS / "authorization_receipt.json",
        {
            "AUTHORIZATION_RECEIPT_SHA256": auth["receipt_sha256"],
            "DATASET_SHA256": DATASET_SHA,
            "EXPERIMENT_ID": EXPERIMENT_ID,
            "GATE_EVAL_SHA256": gate_eval["gate_eval_sha256"],
            "NEXT_ACTION": "TRAIN_V5_STAGE_A_ONCE",
            "READINESS_RECEIPT_SHA256": readiness["receipt_sha256"],
            "TRAINING_CONFIG_SHA256": resolved["training_config_sha256"],
            "TRAIN_AUTHORIZED": True,
            "authorize_rule": AUTHORIZE_RULE,
            "parent_diagnosis": PARENT_DIAGNOSIS,
            "surface_rule": AUTHORIZED_SURFACE_RULE,
            "train": False,
        },
    )

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
